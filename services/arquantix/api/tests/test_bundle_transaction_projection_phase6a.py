"""Tests Phase 6A — projections UX historique bundle (self-trading vs bundle)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundle_execution.bundle_portfolio_transactions import (
    list_bundle_portfolio_transactions,
)
from services.portfolio_engine.bundle_execution.self_trading_projection import (
    detect_suspected_bundle_internal_swap_without_context,
    project_self_trading_transactions,
)
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.test_clients.service import TestClientService

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


@pytest.fixture
def enable_projection_v2(monkeypatch):
    monkeypatch.setenv("BUNDLE_TRANSACTION_PROJECTION_V2_ENABLED", "true")


@pytest.fixture
def disable_projection_v2(monkeypatch):
    monkeypatch.setenv("BUNDLE_TRANSACTION_PROJECTION_V2_ENABLED", "false")


def _bundle_swap_audit(*, portfolio_id: str, batch_id: str, with_execution: bool = True):
    entry = {
        "event": "bundle_leg_context",
        "portfolio_id": portfolio_id,
        "batch_id": batch_id,
        "bundle_action": "allocation",
    }
    if with_execution:
        entry["bundle_execution"] = True
    return [entry]


def _seed_confirmed_swap(
    db: Session,
    pe,
    *,
    audit_log: list,
    from_asset: str = "USDC",
    to_asset: str = "LINK",
    amount_in: str = "16",
) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset=from_asset,
        to_asset=to_asset,
        from_chain="base",
        to_chain="base",
        amount_in=Decimal(amount_in),
        estimated_receive=Decimal("0.5"),
        tx_hash=f"0x{uuid.uuid4().hex}",
        confirmed_at=datetime.now(timezone.utc),
        audit_log=audit_log,
    )
    db.add(swap)
    db.flush()
    return swap


def _fund_and_allocate(
    db: Session,
    pe,
    *,
    portfolio,
    usdc,
    batch_id: str,
    amount: str = "80",
    with_execution: bool = True,
):
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("200"), Decimal("172"))
    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal(amount),
        batch_id=batch_id,
    )
    _seed_confirmed_swap(
        db,
        pe,
        audit_log=_bundle_swap_audit(
            portfolio_id=str(portfolio.id),
            batch_id=batch_id,
            with_execution=with_execution,
        ),
        amount_in="16",
    )


def test_usdc_history_excludes_bundle_allocation_swap(db: Session, enable_projection_v2):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(db, pe, portfolio=portfolio, usdc=usdc, batch_id=batch_id)
    _seed_confirmed_swap(db, pe, audit_log=[], from_asset="USDC", to_asset="EURC")
    db.commit()

    txs = TestClientService().get_crypto_transactions(db, "USDC", client=pe)["transactions"]
    assert not any("LINK" in str(t.get("title") or "") for t in txs)
    assert not any(t.get("transaction_kind") == "bundle_internal_swap" for t in txs)


def test_usdc_history_shows_transfer_to_bundle_negative(db: Session, enable_projection_v2):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(db, pe, portfolio=portfolio, usdc=usdc, batch_id=batch_id)
    db.commit()

    txs = TestClientService().get_crypto_transactions(db, "USDC", client=pe)["transactions"]
    transfer = next(t for t in txs if t.get("transaction_kind") == "bundle_pe_transfer")
    assert transfer["direction"] == "debit"
    assert transfer["amount_crypto"] == "80"
    assert "Crypto" in transfer["title"] or "Bundle" in transfer["title"]


def test_bundle_history_shows_deposit_positive(db: Session, enable_projection_v2):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(db, pe, portfolio=portfolio, usdc=usdc, batch_id=batch_id)
    db.commit()

    txs = list_bundle_portfolio_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    deposit = next(t for t in txs if t.get("transaction_kind") == "bundle_deposit")
    assert deposit["direction"] == "credit"
    assert deposit["amount_crypto"] == "80"
    assert deposit["title"].startswith("Dépôt ·")


def test_bundle_history_aggregates_allocation_by_batch(db: Session, enable_projection_v2):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(db, pe, portfolio=portfolio, usdc=usdc, batch_id=batch_id)
    _seed_confirmed_swap(
        db,
        pe,
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
        to_asset="BTC",
        amount_in="20",
    )
    db.commit()

    txs = list_bundle_portfolio_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    aggregates = [t for t in txs if t.get("transaction_kind") == "bundle_allocation_aggregate"]
    assert len(aggregates) == 1
    agg = aggregates[0]
    assert agg["bundle_batch_id"] == batch_id
    assert agg["legs_count"] == 2
    assert len(agg.get("expandable_legs") or []) == 2
    assert agg["title"].startswith("Allocation ·")


def test_bundle_history_does_not_show_raw_lifi_legs_by_default(db: Session, enable_projection_v2):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(db, pe, portfolio=portfolio, usdc=usdc, batch_id=batch_id)
    db.commit()

    txs = list_bundle_portfolio_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    assert not any(t.get("transaction_kind") == "bundle_internal_swap" for t in txs)


def test_bundle_history_with_ledger_flag_off_still_correct_sign(db: Session, enable_projection_v2):
    """Legacy path (ledger OFF) + projection ON → dépôt positif."""
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(db, pe, portfolio=portfolio, usdc=usdc, batch_id=batch_id)
    db.commit()

    with patch.dict("os.environ", {"BUNDLE_LEDGER_HISTORY_ENABLED": "false"}):
        txs = list_bundle_portfolio_transactions(
            db,
            client_id=pe.id,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
        )
    deposit = next(t for t in txs if t.get("transaction_kind") == "bundle_deposit")
    assert deposit["direction"] == "credit"


def test_bundle_history_with_ledger_flag_on_shows_allocation(db: Session, enable_projection_v2):
    from services.portfolio_engine.bundle_execution.pe_settlement import apply_allocation_leg_atoms
    from tests.test_bundle_ledger_reconciliation import _instrument_cbbtc

    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    cbbtc = _instrument_cbbtc(db)
    batch_id = str(uuid.uuid4())
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("200"), Decimal("172"))
    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("80"),
        batch_id=batch_id,
    )
    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=cbbtc.id,
        entry_asset_consumed=Decimal("16"),
        crypto_received=Decimal("0.001"),
        cost_basis_eur=Decimal("14"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": batch_id,
            "leg_id": "leg-ledger-6a",
            "swap_id": str(uuid.uuid4()),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
        },
    )
    db.commit()

    with patch.dict("os.environ", {"BUNDLE_LEDGER_HISTORY_ENABLED": "true"}):
        txs = list_bundle_portfolio_transactions(
            db,
            client_id=pe.id,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
        )

    assert any(t.get("transaction_kind") == "bundle_deposit" for t in txs)
    assert any(t.get("transaction_kind") == "bundle_allocation_aggregate" for t in txs)


def test_bundle_internal_swap_missing_context_is_detected(db: Session, enable_projection_v2):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(
        db,
        pe,
        portfolio=portfolio,
        usdc=usdc,
        batch_id=batch_id,
        with_execution=False,
    )
    db.commit()

    raw_tx = {
        "id": "x",
        "title": "Échange USDC → LINK",
        "transaction_kind": "crypto_swap",
        "source_system": "lifi_swap",
        "side": "swap",
        "from_asset": "USDC",
        "to_asset": "LINK",
    }
    assert detect_suspected_bundle_internal_swap_without_context(raw_tx) is False

    txs = TestClientService().get_crypto_transactions(db, "USDC", client=pe)["transactions"]
    assert not any("LINK" in str(t.get("title") or "") for t in txs)

    bundle_txs = list_bundle_portfolio_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    assert any(t.get("transaction_kind") == "bundle_allocation_aggregate" for t in bundle_txs)


def test_projection_v2_disabled_preserves_legacy_bundle_sign(db: Session, disable_projection_v2):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    _fund_and_allocate(db, pe, portfolio=portfolio, usdc=usdc, batch_id=batch_id)
    db.commit()

    txs = list_bundle_portfolio_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    assert any(t.get("transaction_kind") == "bundle_pe_transfer" for t in txs)


def test_project_self_trading_filters_bundle_allocation_aggregate():
    raw = [
        {"id": "1", "transaction_kind": "bundle_pe_transfer", "direction": "debit"},
        {"id": "2", "transaction_kind": "bundle_allocation_aggregate"},
        {"id": "3", "transaction_kind": "crypto_swap", "source_system": "bundle_lifi"},
    ]
    filtered = project_self_trading_transactions(raw)
    assert len(filtered) == 1
    assert filtered[0]["id"] == "1"


def test_aggregate_allocation_total_preserves_whole_amounts_ending_in_zero():
    """Regression: rstrip('0') on '80' must not become '8'."""
    from services.portfolio_engine.bundle_execution.bundle_projection import (
        aggregate_bundle_allocations_by_batch,
    )

    batch_id = "batch-80-usdc"
    base = {
        "status": "confirmed",
        "bundle_batch_id": batch_id,
        "external_reference": batch_id,
        "created_at": "2026-05-29T12:00:00+00:00",
        "portfolio_id": "5607e764-dec3-427e-8a88-0c41ff38d61c",
    }
    legs = [
        {**base, "from_asset": "USDC", "asset": "CBETH", "swap_amount_from": "24", "amount_crypto": "0.01"},
        {**base, "from_asset": "USDC", "asset": "CBBTC", "swap_amount_from": "40", "amount_crypto": "0.0005"},
        {**base, "from_asset": "USDC", "asset": "UNI", "swap_amount_from": "5.33328", "amount_crypto": "1.7"},
        {**base, "from_asset": "USDC", "asset": "AAVE", "swap_amount_from": "5.33336", "amount_crypto": "0.06"},
        {**base, "from_asset": "USDC", "asset": "LINK", "swap_amount_from": "5.33336", "amount_crypto": "0.59"},
    ]
    agg = aggregate_bundle_allocations_by_batch(legs, portfolio_name="Crypto Majors")[0]
    assert agg["amount_crypto"] == "80"
    assert agg["asset"] == "USDC"
    assert agg["legs_count"] == 5


def test_aggregate_allocation_total_preserves_30_usdc():
    from services.portfolio_engine.bundle_execution.bundle_projection import (
        aggregate_bundle_allocations_by_batch,
    )

    batch_id = "batch-30-usdc"
    base = {
        "status": "confirmed",
        "bundle_batch_id": batch_id,
        "external_reference": batch_id,
        "created_at": "2026-05-28T12:00:00+00:00",
    }
    legs = [
        {**base, "from_asset": "USDC", "asset": "CBETH", "swap_amount_from": "9", "amount_crypto": "0.004"},
        {**base, "from_asset": "USDC", "asset": "CBBTC", "swap_amount_from": "15", "amount_crypto": "0.0002"},
        {**base, "from_asset": "USDC", "asset": "UNI", "swap_amount_from": "2", "amount_crypto": "0.65"},
        {**base, "from_asset": "USDC", "asset": "AAVE", "swap_amount_from": "2", "amount_crypto": "0.02"},
        {**base, "from_asset": "USDC", "asset": "LINK", "swap_amount_from": "2", "amount_crypto": "0.22"},
    ]
    agg = aggregate_bundle_allocations_by_batch(legs, portfolio_name="Crypto Majors")[0]
    assert agg["amount_crypto"] == "30"
