"""Seuils d'alerte bundle ledger (Phase 4D)."""
from __future__ import annotations

from typing import Any

# Seuils recommandés — voir docs/arquantix/BUNDLE_LEDGER_ALERTING.md
THRESHOLDS = {
    "reconciliation_diff_critical": 0,
    "ledger_history_fallback_warning_after_flag": 0,
    "lock_expired_per_day_warning": 5,
    "failed_partial_withdraw_ops_review": 0,
    "orphan_confirmed_swap_critical": 0,
}


def evaluate_alert_thresholds(
    health: dict[str, Any],
    *,
    history_flag_enabled: bool,
) -> list[dict[str, Any]]:
    """Évalue le rapport health check contre les seuils documentés."""
    alerts: list[dict[str, Any]] = []
    summary = health.get("reconciliation_summary") or {}
    locks = health.get("lock_summary") or {}
    logs = health.get("log_metrics_24h") or {}
    orphans = int(health.get("orphan_confirmed_swaps_total") or 0)

    diff_count = int(summary.get("DIFF") or 0)
    if diff_count > THRESHOLDS["reconciliation_diff_critical"]:
        alerts.append({
            "severity": "critical",
            "code": "reconciliation_diff",
            "message": f"{diff_count} portfolio(s) en verdict DIFF — investiguer immédiatement",
            "value": diff_count,
            "threshold": THRESHOLDS["reconciliation_diff_critical"],
        })

    fallback_24h = int(logs.get("ledger_history_fallback") or 0)
    if history_flag_enabled and fallback_24h > THRESHOLDS["ledger_history_fallback_warning_after_flag"]:
        alerts.append({
            "severity": "warning",
            "code": "ledger_history_fallback",
            "message": (
                f"{fallback_24h} fallback(s) legacy sur 24h après activation flag — "
                "vérifier réconciliation / backfill"
            ),
            "value": fallback_24h,
            "threshold": THRESHOLDS["ledger_history_fallback_warning_after_flag"],
        })

    lock_expired = int(locks.get("invest_lock_expired") or 0) + int(
        locks.get("withdraw_lock_expired") or 0
    )
    if lock_expired > THRESHOLDS["lock_expired_per_day_warning"]:
        alerts.append({
            "severity": "warning",
            "code": "lock_expired",
            "message": f"{lock_expired} lock(s) expired — au-delà du seuil quotidien",
            "value": lock_expired,
            "threshold": THRESHOLDS["lock_expired_per_day_warning"],
        })

    failed_partial = int(locks.get("withdraw_failed_partial") or 0)
    if failed_partial > THRESHOLDS["failed_partial_withdraw_ops_review"]:
        alerts.append({
            "severity": "ops_review",
            "code": "withdraw_failed_partial",
            "message": f"{failed_partial} retrait(s) failed_partial — revue ops requise",
            "value": failed_partial,
            "threshold": THRESHOLDS["failed_partial_withdraw_ops_review"],
        })

    if orphans > THRESHOLDS["orphan_confirmed_swap_critical"]:
        alerts.append({
            "severity": "critical",
            "code": "orphan_confirmed_swap",
            "message": (
                f"{orphans} swap(s) Li.FI confirmé(s) sans entrée ledger — "
                "backfill ou miroir cassé"
            ),
            "value": orphans,
            "threshold": THRESHOLDS["orphan_confirmed_swap_critical"],
        })

    incomplete = int(summary.get("INCOMPLETE") or 0)
    if incomplete > 0:
        alerts.append({
            "severity": "warning",
            "code": "reconciliation_incomplete",
            "message": f"{incomplete} portfolio(s) INCOMPLETE — backfill recommandé",
            "value": incomplete,
            "threshold": 0,
        })

    return alerts


def overall_health_status(alerts: list[dict[str, Any]]) -> str:
    severities = {a.get("severity") for a in alerts}
    if "critical" in severities:
        return "critical"
    if "ops_review" in severities or "warning" in severities:
        return "warning"
    return "ok"
