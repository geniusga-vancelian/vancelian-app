"""Tests Phase 4D — hardening prod ops."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundle_ledger.alerting import (
    THRESHOLDS,
    evaluate_alert_thresholds,
    overall_health_status,
)
from services.portfolio_engine.bundle_ledger.health import run_bundle_ledger_health_check
from services.portfolio_engine.bundle_ledger.log_metrics import parse_log_metrics
from services.portfolio_engine.bundle_ledger.smoke import run_smoke_bundle_ledger_history
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.test_clients.service import TestClientService

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


def test_health_check_counts_diff(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)

    with patch(
        "services.portfolio_engine.bundle_ledger.health.reconcile_bundle_ledger_shadow",
        side_effect=[
            {"verdict": "MATCH", "ledger_entry_count": 3, "orphan_lifi_swaps": []},
            {"verdict": "DIFF", "ledger_entry_count": 2, "orphan_lifi_swaps": [{"swap_id": "x"}]},
        ],
    ):
        report = run_bundle_ledger_health_check(
            db,
            portfolio_limit=2,
        )

    assert report["reconciliation_summary"]["MATCH"] == 1
    assert report["reconciliation_summary"]["DIFF"] == 1
    assert report["health_status"] == "critical"
    assert any(a["code"] == "reconciliation_diff" for a in report["alerts"])
    assert len(report["top_10_investigate"]) >= 1


def test_smoke_detects_self_trading_leak(db: Session):
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

    result = run_smoke_bundle_ledger_history(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    assert result["status"] == "PASS"
    leak_check = next(c for c in result["checks"] if c["name"] == "mon_trading_no_bundle_swap_leak")
    assert leak_check["ok"] is True

    with patch.object(
        TestClientService,
        "get_crypto_transactions",
        return_value={
            "transactions": [{
                "transaction_kind": "bundle_internal_swap",
                "source_system": "lifi_swap",
            }],
        },
    ):
        leaked = run_smoke_bundle_ledger_history(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
        )
    assert leaked["status"] == "FAIL"


def test_alerting_thresholds():
    health = {
        "reconciliation_summary": {"DIFF": 1, "INCOMPLETE": 2, "MATCH": 10},
        "orphan_confirmed_swaps_total": 2,
        "lock_summary": {
            "invest_lock_expired": 6,
            "withdraw_lock_expired": 0,
            "withdraw_failed_partial": 1,
        },
        "log_metrics_24h": {"ledger_history_fallback": 3},
    }
    alerts = evaluate_alert_thresholds(health, history_flag_enabled=True)
    codes = {a["code"] for a in alerts}
    assert "reconciliation_diff" in codes
    assert "orphan_confirmed_swap" in codes
    assert "ledger_history_fallback" in codes
    assert "lock_expired" in codes
    assert "withdraw_failed_partial" in codes
    assert "reconciliation_incomplete" in codes
    assert overall_health_status(alerts) == "critical"
    assert THRESHOLDS["reconciliation_diff_critical"] == 0


def test_log_metrics_parser_24h(tmp_path: Path):
    log_file = tmp_path / "api.log"
    now = datetime.now(timezone.utc).isoformat()
    log_file.write_text(
        f'INFO bundle_ledger.ledger_history_read {{"event": "ledger_history_read", "logged_at": "{now}", "portfolio_id": "p1"}}\n'
        f'WARNING bundle_ledger.ledger_history_fallback {{"event": "ledger_history_fallback", "logged_at": "{now}"}}\n',
        encoding="utf-8",
    )
    metrics = parse_log_metrics([log_file], since_hours=24)
    assert metrics["ledger_history_read"] == 1
    assert metrics["ledger_history_fallback"] == 1


def test_rollback_payload_documented():
    runbook = Path(__file__).resolve().parents[4] / "docs" / "arquantix" / "BUNDLE_LEDGER_GO_LIVE_RUNBOOK.md"
    text = runbook.read_text(encoding="utf-8")
    assert "Rollback détaillé" in text
    assert "BUNDLE_LEDGER_HISTORY_ENABLED=false" in text
    assert "current_history_source" in text
    assert "legacy" in text
    assert "Ne jamais" in text and "DELETE" in text
    assert "reversal" in text.lower() or "BUNDLE_RECOVERY_ADJUSTMENT" in text

    payload_marker = '"flag_enabled": false'
    assert payload_marker in text
