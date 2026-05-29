"""Smoke test historique bundle ledger (Phase 4D)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution.bundle_portfolio_transactions import (
    _list_bundle_portfolio_transactions_legacy,
    list_bundle_portfolio_transactions,
)
from services.portfolio_engine.bundle_ledger.config import bundle_ledger_history_enabled
from services.portfolio_engine.bundle_ledger.history import resolve_history_source
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow
from services.portfolio_engine.bundle_ledger.service import list_bundle_ledger_entries
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio
from services.test_clients.service import TestClientService


def run_smoke_bundle_ledger_history(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    asset: str = "USDC",
) -> dict[str, Any]:
    """Smoke read-only : legacy vs ledger vs Mon Trading isolation."""
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .first()
    )
    if portfolio is None:
        return {"status": "FAIL", "reason": "portfolio_not_found"}

    client = db.query(Client).filter(Client.id == portfolio.client_id).first()
    if client is None or client.person_id != person_id:
        return {"status": "FAIL", "reason": "person_portfolio_mismatch"}

    checks: list[dict[str, Any]] = []

    reconciliation = reconcile_bundle_ledger_shadow(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
    )
    verdict = reconciliation.get("verdict")
    checks.append({"name": "reconciliation", "ok": verdict in ("MATCH", "INCOMPLETE"), "verdict": verdict})

    ledger_shadow = list_bundle_ledger_entries(
        db,
        bundle_portfolio_id=portfolio_id,
        person_id=person_id,
    )
    checks.append({
        "name": "ledger_endpoint_data",
        "ok": ledger_shadow.get("count", 0) >= 0,
        "count": ledger_shadow.get("count"),
    })

    legacy_txs = _list_bundle_portfolio_transactions_legacy(
        db,
        client_id=client.id,
        person_id=person_id,
        portfolio_id=portfolio_id,
        limit=50,
    )
    checks.append({"name": "legacy_history", "ok": True, "count": len(legacy_txs)})

    switched_txs = list_bundle_portfolio_transactions(
        db,
        client_id=client.id,
        person_id=person_id,
        portfolio_id=portfolio_id,
        limit=50,
    )
    history_source, fallback_reason = resolve_history_source(reconciliation)
    expected_source = history_source
    actual_sources = {t.get("source_system") for t in switched_txs}
    if bundle_ledger_history_enabled() and expected_source == "ledger" and verdict == "MATCH":
        history_ok = any(s == "bundle_ledger" for s in actual_sources) or len(switched_txs) == 0
    else:
        history_ok = True
    checks.append({
        "name": "history_switch",
        "ok": history_ok,
        "expected_source": expected_source,
        "fallback_reason": fallback_reason,
        "actual_sources": sorted(s for s in actual_sources if s),
        "count": len(switched_txs),
    })

    svc = TestClientService()
    self_trading = svc.get_crypto_transactions(db, asset=asset, client=client)
    st_txs = self_trading.get("transactions") or []
    leak = any(
        t.get("transaction_kind") == "bundle_internal_swap"
        or (
            t.get("source_system") == "lifi_swap"
            and t.get("transaction_kind") != "bundle_pe_transfer"
        )
        for t in st_txs
    )
    checks.append({
        "name": "mon_trading_no_bundle_swap_leak",
        "ok": not leak,
        "transaction_count": len(st_txs),
    })

    all_ok = all(c.get("ok") for c in checks)
    critical_fail = (
        not checks[-1].get("ok")
        or (verdict == "DIFF")
    )

    return {
        "status": "PASS" if all_ok and not critical_fail else "FAIL",
        "person_id": str(person_id),
        "portfolio_id": str(portfolio_id),
        "flag_enabled": bundle_ledger_history_enabled(),
        "reconciliation_verdict": verdict,
        "checks": checks,
    }
