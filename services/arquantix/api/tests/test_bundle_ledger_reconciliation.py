"""Tests Phase 4A.5 — réconciliation shadow ledger vs PE."""
from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
    release_bundle_cash_leg_to_self_trading,
)
from services.portfolio_engine.bundle_execution.pe_settlement import (
    apply_allocation_leg_atoms,
    apply_withdraw_sell_atoms,
)
from services.portfolio_engine.bundle_ledger.reconciliation import (
    _duplicated_idempotency_keys,
    reconcile_bundle_ledger_shadow,
)
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundle_ledger.service import record_recovery_event
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.instruments.models import Instrument

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


def _instrument_cbbtc(db: Session) -> Instrument:
    asset = db.query(Asset).filter(Asset.symbol == "CBBTC").first()
    if asset is None:
        asset = Asset(symbol="CBBTC", name="Coinbase BTC", asset_type="cryptocurrency")
        db.add(asset)
        db.flush()
    instr = (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )
    if instr is None:
        instr = Instrument(
            asset_id=asset.id,
            code="CBBTC_SPOT",
            name="CBBTC Spot",
            instrument_type="spot",
        )
        db.add(instr)
        db.flush()
    return instr


def test_bundle_ledger_reconciles_deposit_only(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("100"), Decimal("86"))
    batch_id = str(uuid.uuid4())

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("50"),
        batch_id=batch_id,
    )
    db.flush()

    result = reconcile_bundle_ledger_shadow(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    assert result["verdict"] == "MATCH"
    assert result["expected_cash_from_ledger"] == pytest.approx(50.0)
    assert result["actual_cash_from_pe"] == pytest.approx(50.0)
    assert not result["differences"]


def test_bundle_ledger_reconciles_deposit_plus_allocation(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    cbbtc = _instrument_cbbtc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("200"), Decimal("172"))
    batch_id = str(uuid.uuid4())

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("100"),
        batch_id=batch_id,
    )
    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=cbbtc.id,
        entry_asset_consumed=Decimal("60"),
        crypto_received=Decimal("0.001"),
        cost_basis_eur=Decimal("51"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": batch_id,
            "leg_id": "leg-1",
            "swap_id": str(uuid.uuid4()),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
        },
    )
    db.flush()

    result = reconcile_bundle_ledger_shadow(
        db, person_id=pe.person_id, portfolio_id=portfolio.id,
    )
    assert result["verdict"] == "MATCH"
    assert result["expected_cash_from_ledger"] == pytest.approx(40.0)
    assert result["actual_cash_from_pe"] == pytest.approx(40.0)
    assert result["expected_spots_from_ledger"].get("CBBTC") == pytest.approx(0.001)
    assert result["actual_spots_from_pe"].get("CBBTC") == pytest.approx(0.001)


def test_bundle_ledger_reconciles_partial_allocation(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    cbbtc = _instrument_cbbtc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("100"), Decimal("86"))
    batch_id = str(uuid.uuid4())

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("100"),
        batch_id=batch_id,
    )
    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=cbbtc.id,
        entry_asset_consumed=Decimal("50"),
        crypto_received=Decimal("0.0005"),
        cost_basis_eur=Decimal("43"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": batch_id,
            "leg_id": "leg-partial",
            "swap_id": str(uuid.uuid4()),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
        },
    )
    db.flush()

    result = reconcile_bundle_ledger_shadow(
        db, person_id=pe.person_id, portfolio_id=portfolio.id,
    )
    assert result["verdict"] == "MATCH"
    assert result["expected_cash_from_ledger"] == pytest.approx(50.0)
    assert result["actual_cash_from_pe"] == pytest.approx(50.0)


def test_bundle_ledger_reconciles_withdraw_partial(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    cbbtc = _instrument_cbbtc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("150"), Decimal("129"))

    fund_batch = str(uuid.uuid4())
    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("100"),
        batch_id=fund_batch,
    )
    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=cbbtc.id,
        entry_asset_consumed=Decimal("50"),
        crypto_received=Decimal("0.01"),
        cost_basis_eur=Decimal("43"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": fund_batch,
            "leg_id": "leg-alloc",
            "swap_id": str(uuid.uuid4()),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
        },
    )
    withdraw_batch = str(uuid.uuid4())
    apply_withdraw_sell_atoms(
        db,
        portfolio_id=portfolio.id,
        instrument_id=cbbtc.id,
        entry_instrument_id=usdc.id,
        sell_qty=Decimal("0.005"),
        entry_received=Decimal("15"),
        cost_basis_eur=Decimal("400"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": withdraw_batch,
            "leg_id": "leg-w1",
            "swap_id": str(uuid.uuid4()),
            "from_asset": "CBBTC",
            "to_asset": "USDC",
        },
    )
    release_bundle_cash_leg_to_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("20"),
        batch_id=withdraw_batch,
    )
    db.flush()

    result = reconcile_bundle_ledger_shadow(
        db, person_id=pe.person_id, portfolio_id=portfolio.id,
    )
    assert result["verdict"] == "MATCH"
    # 100 fund - 50 alloc + 15 sell - 20 release = 45 cash in bundle
    assert result["expected_cash_from_ledger"] == pytest.approx(45.0)
    assert result["actual_cash_from_pe"] == pytest.approx(45.0)
    assert result["expected_spots_from_ledger"].get("CBBTC") == pytest.approx(0.005)
    assert result["actual_spots_from_pe"].get("CBBTC") == pytest.approx(0.005)


def test_bundle_ledger_detects_missing_entry(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("100"), Decimal("86"))
    batch_id = str(uuid.uuid4())

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("40"),
        batch_id=batch_id,
    )
    db.query(BundleLedgerEntry).filter(
        BundleLedgerEntry.bundle_portfolio_id == portfolio.id,
    ).delete()
    db.flush()

    result = reconcile_bundle_ledger_shadow(
        db, person_id=pe.person_id, portfolio_id=portfolio.id,
    )
    assert result["verdict"] in ("DIFF", "INCOMPLETE")
    assert len(result["missing_ledger_entries"]) >= 1
    assert result["expected_cash_from_ledger"] == pytest.approx(0.0)
    assert result["actual_cash_from_pe"] == pytest.approx(40.0)


def test_bundle_ledger_detects_duplicate_idempotency_key():
    entries = [
        SimpleNamespace(idempotency_key="pe_transfer:batch1:fund:BUNDLE_DEPOSIT:credit"),
        SimpleNamespace(idempotency_key="pe_transfer:batch1:fund:BUNDLE_DEPOSIT:credit"),
        SimpleNamespace(idempotency_key="other:key:here:debit"),
    ]
    dups = _duplicated_idempotency_keys(entries)
    assert dups == ["pe_transfer:batch1:fund:BUNDLE_DEPOSIT:credit"]


def test_bundle_ledger_ignores_recovery_info_for_balances(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("80"), Decimal("68.8"))
    batch_id = str(uuid.uuid4())

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("35"),
        batch_id=batch_id,
    )
    record_recovery_event(
        db,
        person_id=pe.person_id,
        bundle_portfolio_id=portfolio.id,
        batch_id=batch_id,
        reason="invest_lock_ttl_expired",
        lock_type="invest",
        previous_status="pending_signature",
    )
    db.flush()

    result = reconcile_bundle_ledger_shadow(
        db, person_id=pe.person_id, portfolio_id=portfolio.id,
    )
    assert result["verdict"] == "MATCH"
    assert result["expected_cash_from_ledger"] == pytest.approx(35.0)
    assert result["actual_cash_from_pe"] == pytest.approx(35.0)
