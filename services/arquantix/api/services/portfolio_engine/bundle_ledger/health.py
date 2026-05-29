"""Daily health check bundle ledger — read-only (Phase 4D)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundles.bundle_invest_lock import get_invest_lock
from services.portfolio_engine.bundles.bundle_withdraw_lock import (
    RECOVERABLE_WITHDRAW_LOCK_STATUSES,
    get_withdraw_lock,
)
from services.portfolio_engine.bundle_ledger.alerting import (
    evaluate_alert_thresholds,
    overall_health_status,
)
from services.portfolio_engine.bundle_ledger.config import bundle_ledger_history_enabled
from services.portfolio_engine.bundle_ledger.log_metrics import parse_log_metrics
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio

_INVEST_EXPIRED = frozenset({"expired"})
_INVEST_RECOVERABLE = frozenset({"partial", "failed", "expired"})
_WITHDRAW_FAILED_PARTIAL = frozenset({"failed_partial", "partially_unwound"})


def _raw_lock(meta: dict | None, key: str) -> dict[str, Any] | None:
    if not isinstance(meta, dict):
        return None
    raw = meta.get(key)
    return dict(raw) if isinstance(raw, dict) else None


def _scan_lock_summary(portfolios: list[Portfolio]) -> dict[str, int]:
    stats = {
        "invest_lock_expired": 0,
        "invest_lock_recoverable": 0,
        "invest_lock_blocking": 0,
        "withdraw_lock_expired": 0,
        "withdraw_lock_recoverable": 0,
        "withdraw_failed_partial": 0,
        "withdraw_lock_blocking": 0,
    }
    for portfolio in portfolios:
        meta = portfolio.metadata_ if isinstance(portfolio.metadata_, dict) else {}
        invest_active = get_invest_lock(meta)
        invest_raw = _raw_lock(meta, "bundle_invest_lock")
        invest_status = str((invest_active or invest_raw or {}).get("status") or "")
        if invest_status in _INVEST_EXPIRED:
            stats["invest_lock_expired"] += 1
        if invest_status in _INVEST_RECOVERABLE:
            stats["invest_lock_recoverable"] += 1
        if invest_active is not None and invest_status not in _INVEST_RECOVERABLE:
            stats["invest_lock_blocking"] += 1

        withdraw_active = get_withdraw_lock(meta)
        withdraw_raw = _raw_lock(meta, "bundle_withdraw_lock")
        withdraw_status = str((withdraw_active or withdraw_raw or {}).get("status") or "")
        withdraw_phase = str((withdraw_active or withdraw_raw or {}).get("withdraw_phase") or "")
        if withdraw_status == "expired" or withdraw_phase == "EXPIRED":
            stats["withdraw_lock_expired"] += 1
        if withdraw_status in RECOVERABLE_WITHDRAW_LOCK_STATUSES or withdraw_status in _WITHDRAW_FAILED_PARTIAL:
            stats["withdraw_lock_recoverable"] += 1
        if withdraw_status in _WITHDRAW_FAILED_PARTIAL or withdraw_phase == "FAILED_PARTIAL":
            stats["withdraw_failed_partial"] += 1
        if withdraw_active is not None and withdraw_status not in RECOVERABLE_WITHDRAW_LOCK_STATUSES:
            stats["withdraw_lock_blocking"] += 1
    return stats


def _investigation_score(row: dict[str, Any]) -> tuple[int, str]:
    verdict = row.get("verdict") or ""
    priority = {"DIFF": 300, "INCOMPLETE": 200, "MATCH": 0}.get(verdict, 100)
    priority += len(row.get("orphan_lifi_swaps") or []) * 10
    priority += len(row.get("missing_ledger_entries") or [])
    return priority, str(row.get("portfolio_id") or "")


def run_bundle_ledger_health_check(
    db: Session,
    *,
    log_paths: list | None = None,
    since_hours: int = 24,
    portfolio_limit: int | None = None,
) -> dict[str, Any]:
    """Health check read-only quotidien."""
    q = (
        db.query(Portfolio)
        .filter(
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .order_by(Portfolio.updated_at.desc())
    )
    if portfolio_limit:
        q = q.limit(portfolio_limit)
    portfolios = q.all()

    reconciliation_summary = {"MATCH": 0, "INCOMPLETE": 0, "DIFF": 0, "ERROR": 0}
    portfolio_rows: list[dict[str, Any]] = []
    orphan_total = 0

    for portfolio in portfolios:
        client = db.query(Client).filter(Client.id == portfolio.client_id).first()
        if client is None or client.person_id is None:
            reconciliation_summary["ERROR"] += 1
            portfolio_rows.append({
                "portfolio_id": str(portfolio.id),
                "person_id": None,
                "verdict": "ERROR",
                "error": "person_id_missing",
            })
            continue
        try:
            recon = reconcile_bundle_ledger_shadow(
                db,
                person_id=client.person_id,
                portfolio_id=portfolio.id,
            )
            verdict = str(recon.get("verdict") or "ERROR")
            if verdict in reconciliation_summary:
                reconciliation_summary[verdict] += 1
            else:
                reconciliation_summary["ERROR"] += 1
            orphans = recon.get("orphan_lifi_swaps") or []
            orphan_total += len(orphans)
            portfolio_rows.append({
                "portfolio_id": str(portfolio.id),
                "person_id": str(client.person_id),
                "portfolio_name": portfolio.name,
                "verdict": verdict,
                "ledger_entry_count": recon.get("ledger_entry_count"),
                "missing_ledger_entries": recon.get("missing_ledger_entries"),
                "differences": recon.get("differences"),
                "orphan_lifi_swaps": orphans,
            })
        except Exception as exc:
            reconciliation_summary["ERROR"] += 1
            portfolio_rows.append({
                "portfolio_id": str(portfolio.id),
                "person_id": str(client.person_id),
                "verdict": "ERROR",
                "error": str(exc),
            })

    lock_summary = _scan_lock_summary(portfolios)

    log_metrics: dict[str, Any] = {
        "since_hours": since_hours,
        "log_paths": [],
        "ledger_history_read": 0,
        "ledger_history_fallback": 0,
        "note": "Provide --log-file for 24h log metrics",
    }
    if log_paths:
        from pathlib import Path

        paths = [Path(p) for p in log_paths]
        log_metrics = parse_log_metrics(paths, since_hours=since_hours)

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "active_bundle_portfolios": len(portfolios),
        "reconciliation_summary": reconciliation_summary,
        "orphan_confirmed_swaps_total": orphan_total,
        "lock_summary": lock_summary,
        "log_metrics_24h": log_metrics,
        "flag_enabled": bundle_ledger_history_enabled(),
        "portfolio_details": portfolio_rows,
    }

    investigate = sorted(
        [r for r in portfolio_rows if r.get("verdict") != "MATCH"],
        key=_investigation_score,
        reverse=True,
    )[:10]
    report["top_10_investigate"] = investigate

    alerts = evaluate_alert_thresholds(
        report,
        history_flag_enabled=bundle_ledger_history_enabled(),
    )
    report["alerts"] = alerts
    report["health_status"] = overall_health_status(alerts)

    return report
