"""Tests Phase 3A — vault scope funding (trading_available ↔ vault_position)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.vault_execution.vault_funding import (
    VaultFundingError,
    fund_vault_from_self_trading,
    release_vault_to_self_trading,
    resolve_trading_available_for_vault,
    resolve_vault_position_available,
)

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _instrument_usdc


def _seed_trading_usdc(db: Session, client_id: uuid.UUID, amount: Decimal, cost: Decimal):
    direct_pf = ensure_direct_portfolio(db, client_id)
    usdc = _instrument_usdc(db)
    sync_direct_atom(db, direct_pf.id, usdc.id, amount, cost)
    return direct_pf, usdc


def test_fund_vault_moves_trading_to_vault_scope(db: Session):
    pe = make_linked_client(db)
    _, usdc = _seed_trading_usdc(db, pe.id, Decimal("100"), Decimal("86"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    result = fund_vault_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("10"),
        linked_reference_id=ovt_id,
        integration_mode="direct_morpho",
        tx_hash=f"0x{uuid.uuid4().hex}",
    )
    db.flush()

    assert result["skipped"] is False
    assert resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("90")
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("10")

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_available.get("USDC") == Decimal("90")
    assert snap.vault_position.get("USDC") == Decimal("10")

    audit = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action == "vault.fund_from_self_trading",
        )
        .all()
    )
    assert len(audit) == 1
    assert audit[0].metadata_.get("destination_scope") == "vault_position"


def test_release_vault_moves_back_to_trading(db: Session):
    pe = make_linked_client(db)
    _, usdc = _seed_trading_usdc(db, pe.id, Decimal("50"), Decimal("43"))
    fund_ovt = f"cl{uuid.uuid4().hex[:22]}"
    release_ovt = f"cl{uuid.uuid4().hex[:22]}"

    fund_vault_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("20"),
        linked_reference_id=fund_ovt,
    )
    result = release_vault_to_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("8"),
        linked_reference_id=release_ovt,
    )
    db.flush()

    assert result["skipped"] is False
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("12")
    assert resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("38")


def test_fund_vault_preserves_total_usdc_patrimony(db: Session):
    pe = make_linked_client(db)
    _, usdc = _seed_trading_usdc(db, pe.id, Decimal("100"), Decimal("86"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    before_trading = resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id)
    before_vault = resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id)
    total_before = before_trading + before_vault

    fund_vault_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("10"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    after_trading = resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id)
    after_vault = resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id)
    assert after_trading + after_vault == total_before
    assert after_trading == before_trading - Decimal("10")
    assert after_vault == before_vault + Decimal("10")


def test_fund_vault_idempotent_on_same_ovt_id(db: Session):
    pe = make_linked_client(db)
    _, usdc = _seed_trading_usdc(db, pe.id, Decimal("100"), Decimal("86"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    first = fund_vault_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("10"),
        linked_reference_id=ovt_id,
    )
    second = fund_vault_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("10"),
        linked_reference_id=ovt_id,
    )
    db.flush()

    assert first["skipped"] is False
    assert second["skipped"] is True
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("10")
    audit_count = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action == "vault.fund_from_self_trading",
        )
        .count()
    )
    assert audit_count == 1


def test_fund_vault_insufficient_trading_raises(db: Session):
    pe = make_linked_client(db)
    _, usdc = _seed_trading_usdc(db, pe.id, Decimal("5"), Decimal("4.3"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"

    with pytest.raises(VaultFundingError) as exc:
        fund_vault_from_self_trading(
            db,
            client_id=pe.id,
            person_id=pe.person_id,
            asset="USDC",
            instrument_id=usdc.id,
            amount=Decimal("10"),
            linked_reference_id=ovt_id,
        )
    assert exc.value.code == "vault.funding.insufficient_trading_available"
