"""Tests Phase 4A — journal bundle append-only (shadow mode)."""
from __future__ import annotations

import uuid
from decimal import Decimal

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
from services.portfolio_engine.bundle_ledger.enums import (
    BundleLedgerDirection,
    BundleLedgerEventType,
    BundleLedgerSourceSystem,
)
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundle_ledger.service import (
    append_bundle_ledger_entry,
    list_bundle_ledger_entries,
    record_bundle_deposit,
    record_reversal_event,
)
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.test_clients.service import TestClientService

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


def test_bundle_deposit_writes_ledger_entry(db: Session):
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

    rows = (
        db.query(BundleLedgerEntry)
        .filter(
            BundleLedgerEntry.bundle_portfolio_id == portfolio.id,
            BundleLedgerEntry.event_type == BundleLedgerEventType.BUNDLE_DEPOSIT.value,
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].direction == BundleLedgerDirection.CREDIT.value
    assert rows[0].quantity == Decimal("50")
    assert rows[0].batch_id == batch_id
    assert rows[0].source_system == BundleLedgerSourceSystem.PE_TRANSFER.value


def test_bundle_withdrawal_writes_ledger_entry(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc.id, Decimal("40"), Decimal("34"),
    )
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("10"), Decimal("8.6"))
    batch_id = str(uuid.uuid4())

    release_bundle_cash_leg_to_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("25"),
        batch_id=batch_id,
    )
    db.flush()

    rows = (
        db.query(BundleLedgerEntry)
        .filter(
            BundleLedgerEntry.bundle_portfolio_id == portfolio.id,
            BundleLedgerEntry.event_type == BundleLedgerEventType.BUNDLE_WITHDRAWAL.value,
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].direction == BundleLedgerDirection.DEBIT.value
    assert rows[0].quantity == Decimal("25")


def test_allocation_buy_writes_bundle_ledger_only(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    cbbtc = _instrument_cbbtc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc.id, Decimal("100"), Decimal("86"),
    )
    swap_id = uuid.uuid4()
    batch_id = str(uuid.uuid4())

    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=cbbtc.id,
        entry_asset_consumed=Decimal("50"),
        crypto_received=Decimal("0.001"),
        cost_basis_eur=Decimal("43"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": batch_id,
            "leg_id": "leg-1",
            "swap_id": str(swap_id),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
        },
    )
    db.flush()

    rows = (
        db.query(BundleLedgerEntry)
        .filter(BundleLedgerEntry.bundle_portfolio_id == portfolio.id)
        .all()
    )
    event_types = {r.event_type for r in rows}
    assert BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value in event_types
    assert BundleLedgerEventType.BUNDLE_CASH_RELEASED.value in event_types
    assert len(rows) == 2


def test_withdraw_sell_writes_bundle_ledger_only(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    cbbtc = _instrument_cbbtc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    BundleOrchestrator._sync_pe_position(
        db, portfolio.id, cbbtc.id, Decimal("0.01"), Decimal("800"),
    )
    swap_id = uuid.uuid4()
    batch_id = str(uuid.uuid4())

    apply_withdraw_sell_atoms(
        db,
        portfolio_id=portfolio.id,
        instrument_id=cbbtc.id,
        entry_instrument_id=usdc.id,
        sell_qty=Decimal("0.005"),
        entry_received=Decimal("200"),
        cost_basis_eur=Decimal("400"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": batch_id,
            "leg_id": "leg-w1",
            "swap_id": str(swap_id),
            "from_asset": "CBBTC",
            "to_asset": "USDC",
        },
    )
    db.flush()

    rows = (
        db.query(BundleLedgerEntry)
        .filter(BundleLedgerEntry.bundle_portfolio_id == portfolio.id)
        .all()
    )
    sells = [r for r in rows if r.event_type == BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value]
    assert len(sells) == 1
    assert sells[0].metadata_.get("withdraw_sell") is True


def test_bundle_ledger_idempotent_on_retry(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())

    record_bundle_deposit(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        bundle_portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("10"),
        batch_id=batch_id,
    )
    record_bundle_deposit(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        bundle_portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("10"),
        batch_id=batch_id,
    )
    db.flush()

    count = (
        db.query(BundleLedgerEntry)
        .filter(
            BundleLedgerEntry.bundle_portfolio_id == portfolio.id,
            BundleLedgerEntry.batch_id == batch_id,
        )
        .count()
    )
    assert count == 1


def test_bundle_ledger_reversal_event_not_update(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())

    original = append_bundle_ledger_entry(
        db,
        person_id=pe.person_id,
        bundle_portfolio_id=portfolio.id,
        event_type=BundleLedgerEventType.BUNDLE_DEPOSIT.value,
        asset_symbol="USDC",
        quantity=Decimal("15"),
        direction=BundleLedgerDirection.CREDIT.value,
        source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
        source_id=f"{batch_id}:fund",
        batch_id=batch_id,
    )
    original_qty = original.quantity
    original_status = original.status

    reversal = record_reversal_event(
        db,
        original=original,
        reason="test_correction",
    )
    db.flush()
    db.refresh(original)

    assert original.quantity == original_qty
    assert original.status == original_status
    assert reversal.event_type == BundleLedgerEventType.BUNDLE_RECOVERY_ADJUSTMENT.value
    assert reversal.direction == BundleLedgerDirection.DEBIT.value
    assert reversal.metadata_.get("reversal_of_entry_id") == str(original.id)

    total = (
        db.query(BundleLedgerEntry)
        .filter(BundleLedgerEntry.bundle_portfolio_id == portfolio.id)
        .count()
    )
    assert total == 2


def test_bundle_ledger_entries_not_visible_in_self_trading(db: Session):
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
        amount=Decimal("30"),
        batch_id=batch_id,
    )
    db.flush()

    svc = TestClientService()
    result = svc.get_crypto_transactions(
        db,
        asset="USDC",
        client=pe,
    )
    txs = result["transactions"]
    ledger_ids = {
        str(r.id)
        for r in db.query(BundleLedgerEntry.id)
        .filter(BundleLedgerEntry.bundle_portfolio_id == portfolio.id)
        .all()
    }
    tx_ids = {str(t.get("id")) for t in txs if t.get("id")}
    assert ledger_ids.isdisjoint(tx_ids)
    assert not any(t.get("source_system") == "bundle_ledger" for t in txs)


def test_bundle_history_can_read_from_ledger_shadow(db: Session):
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
        amount=Decimal("20"),
        batch_id=batch_id,
    )
    db.flush()

    shadow = list_bundle_ledger_entries(
        db,
        bundle_portfolio_id=portfolio.id,
        person_id=pe.person_id,
    )
    assert shadow["shadow_mode"] is True
    assert shadow["count"] >= 1
    assert any(e["event_type"] == "BUNDLE_DEPOSIT" for e in shadow["entries"])
    assert len(shadow["cash_movements"]) >= 1
    assert shadow["source_links"]
