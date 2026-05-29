"""Tests Phase 4C — rollout prod limitée + monitoring."""
from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundle_ledger.admin_payload import enrich_admin_reconciliation_payload
from services.portfolio_engine.bundle_ledger.history import maybe_list_bundle_transactions_from_ledger
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow
from services.portfolio_engine.bundle_ledger.rollout import validate_portfolio_rollout, validate_rollout_panel
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


def test_rollout_validation_match(db: Session):
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
        amount=Decimal("42"),
        batch_id=batch_id,
    )
    db.flush()

    result = validate_portfolio_rollout(
        db,
        portfolio_id=portfolio.id,
        apply_backfill=False,
    )
    assert result["verdict"] == "MATCH"
    assert result["rollout_ready"] is True
    assert result["history_source_expected"] in ("ledger", "legacy")

    panel = validate_rollout_panel(db, portfolio_ids=[portfolio.id])
    assert panel["rollout_status"] == "ready"
    assert panel["summary"]["MATCH"] == 1


def test_rollout_validation_diff_fails(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    monkeypatch.setattr(
        "services.portfolio_engine.bundle_ledger.config.bundle_ledger_history_enabled",
        lambda: True,
    )

    with patch(
        "services.portfolio_engine.bundle_ledger.rollout.reconcile_bundle_ledger_shadow",
        return_value={
            "verdict": "DIFF",
            "ledger_entry_count": 2,
            "differences": [{"field": "cash_leg"}],
        },
    ):
        result = validate_portfolio_rollout(
            db,
            portfolio_id=portfolio.id,
            apply_backfill=False,
        )
        panel = validate_rollout_panel(db, portfolio_ids=[portfolio.id])

    assert result["verdict"] == "DIFF"
    assert result["rollout_ready"] is False
    assert result["fallback_reason"] == "ledger_diff"

    assert panel["rollout_status"] == "not_ready"
    assert panel["summary"]["DIFF"] == 1


def test_history_source_admin_payload(db: Session, monkeypatch):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("50"), Decimal("43"))
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

    monkeypatch.setenv("BUNDLE_LEDGER_HISTORY_ENABLED", "true")
    payload = reconcile_bundle_ledger_shadow(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    enriched = enrich_admin_reconciliation_payload(payload, portfolio=portfolio)

    assert enriched["verdict"] == "MATCH"
    assert enriched["flag_enabled"] is True
    assert enriched["current_history_source"] == "ledger"
    assert enriched["fallback_reason"] is None
    assert "last_backfill_summary" in enriched


def test_ledger_history_logs_fallback_reason(db: Session, monkeypatch, caplog):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    monkeypatch.setenv("BUNDLE_LEDGER_HISTORY_ENABLED", "true")

    with caplog.at_level(logging.INFO, logger="bundle_ledger.observability"):
        txs, meta = maybe_list_bundle_transactions_from_ledger(
            db,
            client_id=pe.id,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
        )

    assert txs is None
    assert meta is not None
    assert meta.get("source") == "legacy"

    fallback_logs = [
        r for r in caplog.records
        if "ledger_history_fallback" in r.getMessage()
    ]
    assert len(fallback_logs) >= 1
    msg = fallback_logs[0].getMessage()
    assert "ledger_incomplete_or_empty" in msg
    payload = json.loads(msg[msg.index("{"):])
    assert payload["event"] == "ledger_history_fallback"
    assert payload["portfolio_id"] == str(portfolio.id)
    assert payload.get("fallback_reason") == "ledger_incomplete_or_empty"


def test_rollout_panel_not_ready_on_incomplete(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    from services.portfolio_engine.hardening.audit_models import AuditEvent
    from datetime import datetime, timezone

    db.add(
        AuditEvent(
            id=uuid.uuid4(),
            entity_type="portfolio",
            entity_id=str(portfolio.id),
            action="bundle.fund_cash_leg",
            actor_id="test",
            metadata_={
                "client_id": str(pe.id),
                "portfolio_id": str(portfolio.id),
                "batch_id": str(uuid.uuid4()),
                "entry_asset": "USDC",
                "amount": "10",
            },
            created_at=datetime.now(timezone.utc),
        )
    )
    db.flush()

    panel = validate_rollout_panel(db, portfolio_ids=[portfolio.id])
    assert panel["rollout_status"] == "not_ready"
    assert panel["summary"]["INCOMPLETE"] >= 1 or panel["summary"]["DIFF"] >= 1
