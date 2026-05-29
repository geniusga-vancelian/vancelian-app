"""Tests Phase 4B — historique bundle lu depuis ledger (feature flag)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundle_execution.bundle_portfolio_transactions import (
    _list_bundle_portfolio_transactions_legacy,
    list_bundle_portfolio_transactions,
)
from services.portfolio_engine.bundle_execution.pe_settlement import apply_allocation_leg_atoms
from services.portfolio_engine.bundle_ledger.enums import BundleLedgerEventType
from services.portfolio_engine.bundle_ledger.history import ledger_entry_to_bundle_tx
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.test_clients.service import TestClientService

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc
from tests.test_bundle_ledger_reconciliation import _instrument_cbbtc


@pytest.fixture
def enable_ledger_history(monkeypatch):
    monkeypatch.setenv("BUNDLE_LEDGER_HISTORY_ENABLED", "true")


def test_bundle_history_reads_ledger_when_flag_enabled(db: Session, enable_ledger_history):
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
        amount=Decimal("55"),
        batch_id=batch_id,
    )
    db.flush()

    txs = list_bundle_portfolio_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    assert len(txs) >= 1
    assert any(t.get("source_system") == "bundle_ledger" for t in txs)
    assert any(t.get("transaction_kind") == "bundle_deposit" for t in txs)


def test_bundle_history_falls_back_on_incomplete_ledger(db: Session, enable_ledger_history):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())

    from services.portfolio_engine.hardening.audit_models import AuditEvent

    db.add(
        AuditEvent(
            id=uuid.uuid4(),
            entity_type="portfolio",
            entity_id=str(portfolio.id),
            action="bundle.fund_cash_leg",
            actor_id=f"test:{batch_id}",
            metadata_={
                "client_id": str(pe.id),
                "portfolio_id": str(portfolio.id),
                "batch_id": batch_id,
                "entry_asset": "USDC",
                "amount": "10",
            },
            created_at=datetime.now(timezone.utc),
        )
    )
    db.flush()

    legacy = _list_bundle_portfolio_transactions_legacy(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    switched = list_bundle_portfolio_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    assert len(legacy) >= 1
    assert len(switched) >= 1
    assert all(t.get("source_system") != "bundle_ledger" for t in switched)


def test_bundle_history_falls_back_on_diff_ledger(db: Session, enable_ledger_history):
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

    with patch(
        "services.portfolio_engine.bundle_ledger.history.reconcile_bundle_ledger_shadow",
        return_value={"verdict": "DIFF", "differences": [{"field": "cash_leg"}]},
    ):
        txs = list_bundle_portfolio_transactions(
            db,
            client_id=pe.id,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
        )
    assert all(t.get("source_system") != "bundle_ledger" for t in txs)


def test_self_trading_history_unchanged_when_ledger_history_enabled(
    db: Session,
    enable_ledger_history,
):
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
        amount=Decimal("25"),
        batch_id=batch_id,
    )
    db.flush()

    svc = TestClientService()
    result = svc.get_crypto_transactions(db, asset="USDC", client=pe)
    kinds = {t.get("transaction_kind") for t in result["transactions"]}
    assert "bundle_internal_swap" not in kinds
    assert not any(t.get("source_system") == "bundle_ledger" for t in result["transactions"])


def test_ledger_history_formats_deposit_allocation_withdrawal(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    cbbtc = _instrument_cbbtc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("200"), Decimal("172"))

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
        entry_asset_consumed=Decimal("40"),
        crypto_received=Decimal("0.001"),
        cost_basis_eur=Decimal("34"),
        ledger={
            "person_id": str(pe.person_id),
            "batch_id": fund_batch,
            "leg_id": "leg-fmt",
            "swap_id": str(uuid.uuid4()),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
        },
    )
    withdraw_batch = str(uuid.uuid4())
    from services.portfolio_engine.bundle_execution.bundle_funding import (
        release_bundle_cash_leg_to_self_trading,
    )

    release_bundle_cash_leg_to_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("15"),
        batch_id=withdraw_batch,
    )
    db.flush()

    rows = (
        db.query(BundleLedgerEntry)
        .filter(BundleLedgerEntry.bundle_portfolio_id == portfolio.id)
        .order_by(BundleLedgerEntry.created_at.asc())
        .all()
    )
    formatted = [
        ledger_entry_to_bundle_tx(r, portfolio_name=portfolio.name)
        for r in rows
    ]
    formatted = [f for f in formatted if f is not None]
    kinds = {f.get("transaction_kind") for f in formatted}
    assert "bundle_deposit" in kinds
    assert "bundle_internal_swap" in kinds
    titles = [f.get("title") or "" for f in formatted]
    assert any(t.startswith("Dépôt ·") for t in titles)
    assert any("Allocation" in t for t in titles)
    assert any(t.startswith("Retrait ·") for t in titles)
