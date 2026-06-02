"""Tests Phase 3B — Lombard scope funding (lock collateral + borrow USDC)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.direct_overlay import (
    _resolve_or_create_instrument,
    ensure_direct_portfolio,
    sync_direct_atom,
)
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.lombard_execution.lombard_funding import (
    LombardFundingError,
    credit_lombard_borrow_to_trading,
    lock_lombard_collateral_from_trading,
    open_lombard_loan,
    resolve_lombard_liability_usdc,
    resolve_trading_available_for_lombard,
    resolve_trading_locked_collateral_for_lombard,
)
from tests.conftest import make_linked_client
from tests.test_bundle_lifi_funding import _instrument_usdc


def _instrument_cbbtc(db: Session):
    return _resolve_or_create_instrument(db, "CBBTC")


def _instrument_cbeth(db: Session):
    return _resolve_or_create_instrument(db, "CBETH")


def _seed_trading_asset(
    db: Session,
    client_id: uuid.UUID,
    instrument,
    amount: Decimal,
    cost: Decimal,
):
    direct_pf = ensure_direct_portfolio(db, client_id)
    sync_direct_atom(db, direct_pf.id, instrument.id, amount, cost)
    return direct_pf, instrument


def test_lock_collateral_debits_trading_available_and_credits_locked(db: Session):
    pe = make_linked_client(db)
    cbbtc = _instrument_cbbtc(db)
    _seed_trading_asset(db, pe.id, cbbtc, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    result = lock_lombard_collateral_from_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="CBBTC",
        instrument_id=cbbtc.id,
        amount=Decimal("0.000125"),
        linked_reference_id=ovt_id,
        integration_mode="lombard_v1",
    )
    db.flush()

    assert result["skipped"] is False
    assert resolve_trading_available_for_lombard(db, client_id=pe.id, instrument_id=cbbtc.id) == Decimal(
        "0.000875"
    )
    assert resolve_trading_locked_collateral_for_lombard(
        db, client_id=pe.id, instrument_id=cbbtc.id
    ) == Decimal("0.000125")

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_available.get("CBBTC") == Decimal("0.000875")
    assert snap.trading_locked_collateral.get("CBBTC") == Decimal("0.000125")


def test_borrow_credits_liability_and_trading_usdc(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    result = credit_lombard_borrow_to_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("5"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    assert result["skipped"] is False
    assert resolve_trading_available_for_lombard(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("5")
    assert resolve_lombard_liability_usdc(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("5")

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_available.get("USDC") == Decimal("5")
    assert snap.liability.get("USDC") == Decimal("5")


def test_open_loan_atomic_lock_then_borrow(db: Session):
    pe = make_linked_client(db)
    cbbtc = _instrument_cbbtc(db)
    usdc = _instrument_usdc(db)
    _seed_trading_asset(db, pe.id, cbbtc, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    result = open_lombard_loan(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        collateral_asset="CBBTC",
        collateral_instrument_id=cbbtc.id,
        collateral_amount=Decimal("0.000125"),
        borrow_amount=Decimal("5"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    assert result["lock"]["skipped"] is False
    assert result["borrow"]["skipped"] is False
    assert resolve_trading_locked_collateral_for_lombard(
        db, client_id=pe.id, instrument_id=cbbtc.id
    ) == Decimal("0.000125")
    assert resolve_trading_available_for_lombard(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("5")
    assert resolve_lombard_liability_usdc(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("5")

    audits = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == ovt_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    assert len(audits) == 2
    assert {a.action for a in audits} == {"lombard.lock_collateral", "lombard.open_borrow"}


def test_open_loan_idempotent_double_call(db: Session):
    pe = make_linked_client(db)
    cbbtc = _instrument_cbbtc(db)
    usdc = _instrument_usdc(db)
    _seed_trading_asset(db, pe.id, cbbtc, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    first = open_lombard_loan(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        collateral_asset="CBBTC",
        collateral_instrument_id=cbbtc.id,
        collateral_amount=Decimal("0.000125"),
        borrow_amount=Decimal("5"),
        linked_reference_id=ovt_id,
    )
    second = open_lombard_loan(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        collateral_asset="CBBTC",
        collateral_instrument_id=cbbtc.id,
        collateral_amount=Decimal("0.000125"),
        borrow_amount=Decimal("5"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    assert first["lock"]["skipped"] is False
    assert second["lock"]["skipped"] is True
    assert second["borrow"]["skipped"] is True
    assert (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == ovt_id)
        .count()
    ) == 2


def test_insufficient_collateral_raises_no_borrow(db: Session):
    pe = make_linked_client(db)
    cbbtc = _instrument_cbbtc(db)
    usdc = _instrument_usdc(db)
    _seed_trading_asset(db, pe.id, cbbtc, Decimal("0.00001"), Decimal("1"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    with pytest.raises(LombardFundingError) as exc:
        open_lombard_loan(
            db,
            client_id=pe.id,
            person_id=pe.person_id,
            collateral_asset="CBBTC",
            collateral_instrument_id=cbbtc.id,
            collateral_amount=Decimal("0.000125"),
            borrow_amount=Decimal("5"),
            linked_reference_id=ovt_id,
        )
    assert exc.value.code == "lombard.lock.insufficient_trading_available"
    assert resolve_trading_available_for_lombard(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("0")
    assert resolve_lombard_liability_usdc(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("0")
    assert db.query(AuditEvent).filter(AuditEvent.entity_id == ovt_id).count() == 0


def test_cbbtc_8_decimals_lock(db: Session):
    pe = make_linked_client(db)
    cbbtc = _instrument_cbbtc(db)
    _seed_trading_asset(db, pe.id, cbbtc, Decimal("0.1"), Decimal("5000"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    lock_lombard_collateral_from_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="CBBTC",
        instrument_id=cbbtc.id,
        amount=Decimal("0.000125"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    assert resolve_trading_locked_collateral_for_lombard(
        db, client_id=pe.id, instrument_id=cbbtc.id
    ) == Decimal("0.000125")


def test_cbeth_18_decimals_lock(db: Session):
    pe = make_linked_client(db)
    cbeth = _instrument_cbeth(db)
    _seed_trading_asset(db, pe.id, cbeth, Decimal("1"), Decimal("3000"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    lock_lombard_collateral_from_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="CBETH",
        instrument_id=cbeth.id,
        amount=Decimal("0.003085961700228149"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    locked = resolve_trading_locked_collateral_for_lombard(
        db, client_id=pe.id, instrument_id=cbeth.id
    )
    assert locked == Decimal("0.0030859617")


def test_open_loan_preserves_total_collateral_patrimony(db: Session):
    pe = make_linked_client(db)
    cbbtc = _instrument_cbbtc(db)
    _seed_trading_asset(db, pe.id, cbbtc, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    before_available = resolve_trading_available_for_lombard(db, client_id=pe.id, instrument_id=cbbtc.id)
    before_locked = resolve_trading_locked_collateral_for_lombard(db, client_id=pe.id, instrument_id=cbbtc.id)
    total_before = before_available + before_locked

    open_lombard_loan(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        collateral_asset="CBBTC",
        collateral_instrument_id=cbbtc.id,
        collateral_amount=Decimal("0.000125"),
        borrow_amount=Decimal("0"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    after_available = resolve_trading_available_for_lombard(db, client_id=pe.id, instrument_id=cbbtc.id)
    after_locked = resolve_trading_locked_collateral_for_lombard(db, client_id=pe.id, instrument_id=cbbtc.id)
    assert after_available + after_locked == total_before


def test_pe_reader_sees_locked_and_liability(db: Session):
    pe = make_linked_client(db)
    cbbtc = _instrument_cbbtc(db)
    usdc = _instrument_usdc(db)
    _seed_trading_asset(db, pe.id, cbbtc, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    open_lombard_loan(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        collateral_asset="CBBTC",
        collateral_instrument_id=cbbtc.id,
        collateral_amount=Decimal("0.000125"),
        borrow_amount=Decimal("5"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_locked_collateral.get("CBBTC") == Decimal("0.000125")
    assert snap.trading_available.get("USDC") == Decimal("5")
    assert snap.liability.get("USDC") == Decimal("5")
