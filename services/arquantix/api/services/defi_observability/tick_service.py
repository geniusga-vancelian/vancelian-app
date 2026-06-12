"""Orchestration tick observabilité DeFi (Phase 9)."""
from __future__ import annotations

import logging
import os
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from services.onchain_indexer.chain_config import CHAIN_BASE, resolve_chain_id
from services.onchain_indexer.continuous_base_indexer import (
    IndexerConfigError,
    IndexerNotEnabledError,
    run_base_indexer_once,
)
from services.onchain_indexer.indexer_config import BaseIndexerConfig
from services.onchain_indexer.models import TransactionIntent
from services.onchain_reconciliation.discrepancy_models import ReconciliationDiscrepancy
from services.onchain_reconciliation.user_reconcile import build_user_reconcile_report
from services.transaction_intents.enums import IntentProductType
from services.transaction_intents.transaction_intent_health import (
    build_admin_health_payload,
    list_stale_intents,
    reconcile_stale_intents,
)

from .job_run_repository import JOB_NAME_TICK, DefiJobRunRepository
from .models import DefiObservabilityJobRun

logger = logging.getLogger(__name__)

P1_PRODUCTS = frozenset(
    {
        IntentProductType.LOMBARD_BORROW.value,
        IntentProductType.BUNDLE_INVEST.value,
    }
)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw.isdigit() else default


def list_recent_active_person_ids(
    db: Session,
    *,
    hours: int = 48,
    limit: int = 25,
) -> list[UUID]:
    """Personnes avec activité intent récente (proxy users actifs DeFi)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        db.query(TransactionIntent.person_id)
        .filter(
            TransactionIntent.person_id.isnot(None),
            TransactionIntent.updated_at >= cutoff,
        )
        .group_by(TransactionIntent.person_id)
        .order_by(func.max(TransactionIntent.updated_at).desc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows if r[0] is not None]


def compute_ops_alerts(
    db: Session,
    *,
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    indexer = summary.get("indexer") or {}
    if indexer.get("error"):
        alerts.append(
            {
                "level": "error",
                "code": "indexer_step_failed",
                "message": str(indexer.get("error")),
            }
        )
    elif indexer.get("errors"):
        for err in indexer.get("errors") or []:
            alerts.append(
                {
                    "level": "error",
                    "code": "indexer_rpc_error",
                    "message": str(err),
                }
            )

    health = summary.get("health") or {}
    for stale in health.get("stale_preview") or []:
        if stale.get("severity") == "P1" and stale.get("product_type") in P1_PRODUCTS:
            alerts.append(
                {
                    "level": "warning",
                    "code": "stale_intent_p1",
                    "message": (
                        f"Intent stale P1 {stale.get('product_type')} "
                        f"{stale.get('status')} ({stale.get('intent_id')})"
                    ),
                    "product_type": stale.get("product_type"),
                    "intent_id": stale.get("intent_id"),
                }
            )

    try:
        from services.portfolio_engine.bundles.bundle_v3_deposit_flow.config import (
            bundle_v3_deposit_worker_enabled,
        )
        from services.portfolio_engine.bundles.bundle_v3_deposit_flow.ops_alerts import (
            bundle_v3_ops_alerts_for_tick,
        )

        if bundle_v3_deposit_worker_enabled():
            alerts.extend(bundle_v3_ops_alerts_for_tick(db))
    except Exception as exc:
        alerts.append(
            {
                "level": "warning",
                "code": "bundle_v3_ops_audit_failed",
                "message": str(exc)[:500],
            }
        )

    p0_threshold = _env_int("DEFI_OPS_OPEN_P0_THRESHOLD", 3)
    p1_threshold = _env_int("DEFI_OPS_OPEN_P1_THRESHOLD", 10)
    open_p0 = (
        db.query(func.count(ReconciliationDiscrepancy.id))
        .filter(
            ReconciliationDiscrepancy.status == "open",
            ReconciliationDiscrepancy.severity == "P0",
        )
        .scalar()
        or 0
    )
    open_p1 = (
        db.query(func.count(ReconciliationDiscrepancy.id))
        .filter(
            ReconciliationDiscrepancy.status == "open",
            ReconciliationDiscrepancy.severity == "P1",
        )
        .scalar()
        or 0
    )
    if open_p0 >= p0_threshold:
        alerts.append(
            {
                "level": "critical",
                "code": "open_discrepancies_p0_high",
                "message": f"{open_p0} discrepancies P0 ouvertes (>={p0_threshold})",
                "count": open_p0,
            }
        )
    if open_p1 >= p1_threshold:
        alerts.append(
            {
                "level": "warning",
                "code": "open_discrepancies_p1_high",
                "message": f"{open_p1} discrepancies P1 ouvertes (>={p1_threshold})",
                "count": open_p1,
            }
        )

    summary["open_discrepancies"] = {"P0": int(open_p0), "P1": int(open_p1)}

    return alerts


def _overall_status(
    *,
    fatal_error: Optional[str],
    step_errors: list[str],
    alerts: list[dict[str, Any]],
) -> str:
    if fatal_error:
        return "error"
    if step_errors:
        return "degraded"
    if any(a.get("level") == "critical" for a in alerts):
        return "degraded"
    if any(a.get("level") == "error" for a in alerts):
        return "degraded"
    return "success"


def _elapsed_exceeded(
    started_mono: float,
    max_duration_seconds: Optional[int],
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> bool:
    if max_duration_seconds is None or max_duration_seconds <= 0:
        return False
    return (monotonic() - started_mono) > float(max_duration_seconds)


def record_skipped_locked_tick(
    db: Session,
    *,
    persist_job_run: bool = True,
) -> dict[str, Any]:
    """Enregistre un run sans exécuter le tick (verrou advisory déjà pris)."""
    summary: dict[str, Any] = {
        "dry_run": False,
        "job_name": JOB_NAME_TICK,
        "overall_status": "skipped_locked",
        "reason": "another defi_observability_tick holds the PostgreSQL advisory lock",
        "steps": {},
    }
    if persist_job_run:
        job_row = DefiJobRunRepository.create(db, job_name=JOB_NAME_TICK)
        DefiJobRunRepository.finish(
            db,
            job_row,
            status="skipped_locked",
            summary_json=summary,
            error_json=None,
        )
        summary["job_run_id"] = str(job_row.id)
    return summary


def _finalize_tick_summary(
    db: Session,
    *,
    job_row: Optional[DefiObservabilityJobRun],
    summary: dict[str, Any],
    step_errors: list[str],
    fatal_error: Optional[str],
    overall_status: str,
) -> None:
    summary["overall_status"] = overall_status
    summary["step_errors"] = step_errors
    if job_row is not None:
        DefiJobRunRepository.finish(
            db,
            job_row,
            status=overall_status,
            summary_json=summary,
            error_json={"step_errors": step_errors} if step_errors else None,
        )
        summary["job_run_id"] = str(job_row.id)


def run_defi_observability_tick(
    db: Session,
    *,
    dry_run: bool = True,
    max_users: int = 25,
    user_hours: int = 48,
    chain: str = "base",
    persist_job_run: bool = True,
    max_duration_seconds: Optional[int] = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """
    Enchaîne indexer --once, health, reconcile users récents.
    Écritures autorisées en no-dry-run : raw events, checkpoints, discrepancies, job_runs.
    """
    job_row = None
    if persist_job_run and not dry_run:
        job_row = DefiJobRunRepository.create(db, job_name=JOB_NAME_TICK)

    summary: dict[str, Any] = {
        "dry_run": dry_run,
        "job_name": JOB_NAME_TICK,
        "would_write": [] if dry_run else [
            "raw_onchain_events",
            "onchain_indexer_checkpoints",
            "reconciliation_discrepancies",
            "defi_observability_job_runs",
        ],
        "steps": {},
    }
    step_errors: list[str] = []
    fatal_error: Optional[str] = None
    started_mono = monotonic()

    def _timeout_before(step: str) -> bool:
        if not _elapsed_exceeded(
            started_mono,
            max_duration_seconds,
            monotonic=monotonic,
        ):
            return False
        summary["timeout"] = True
        summary["stopped_before_step"] = step
        summary["steps"]["timeout"] = {
            "max_duration_seconds": max_duration_seconds,
            "stopped_before_step": step,
        }
        return True

    try:
        chain_id = resolve_chain_id(chain)
        cfg = BaseIndexerConfig.from_env()

        if _timeout_before("indexer"):
            summary["alerts"] = compute_ops_alerts(db, summary=summary)
            _finalize_tick_summary(
                db,
                job_row=job_row,
                summary=summary,
                step_errors=step_errors,
                fatal_error=None,
                overall_status="timeout_degraded",
            )
            return summary

        # 1 — Indexer
        try:
            indexer_result = run_base_indexer_once(
                db,
                chain_id=chain_id,
                dry_run=dry_run,
                config=cfg,
                force_write=False,
            )
            summary["indexer"] = indexer_result.to_dict()
            summary["steps"]["indexer"] = {
                "status": indexer_result.status,
                "dry_run": dry_run,
                "events_inserted": (indexer_result.erc20 or {}).get("inserted", 0),
                "errors_count": len(indexer_result.errors),
            }
            if indexer_result.errors:
                step_errors.append("indexer_errors")
        except (IndexerNotEnabledError, IndexerConfigError) as exc:
            summary["indexer"] = {"skipped": True, "error": str(exc)}
            summary["steps"]["indexer"] = {"skipped": True, "error": str(exc)}
            step_errors.append("indexer_skipped")
        except Exception as exc:
            summary["indexer"] = {"error": str(exc)}
            summary["steps"]["indexer"] = {"error": str(exc)}
            step_errors.append("indexer_failed")
            logger.warning("defi_observability.indexer_failed", exc_info=True)

        if _timeout_before("intent_health"):
            summary["alerts"] = compute_ops_alerts(db, summary=summary)
            _finalize_tick_summary(
                db,
                job_row=job_row,
                summary=summary,
                step_errors=step_errors,
                fatal_error=None,
                overall_status="timeout_degraded",
            )
            return summary

        # 2 — Intent health + stale reconcile
        try:
            health = build_admin_health_payload(db)
            stale_report = reconcile_stale_intents(db, dry_run=dry_run, limit=500)
            summary["health"] = health
            summary["stale_reconcile"] = stale_report
            summary["steps"]["intent_health"] = {
                "stale_detected": stale_report.get("stale_detected", 0),
                "discrepancies_written": stale_report.get("discrepancies_written", 0),
                "dry_run": dry_run,
            }
        except Exception as exc:
            summary["health"] = {"error": str(exc)}
            summary["steps"]["intent_health"] = {"error": str(exc)}
            step_errors.append("intent_health_failed")
            logger.warning("defi_observability.health_failed", exc_info=True)

        if _timeout_before("swap_maintenance"):
            summary["alerts"] = compute_ops_alerts(db, summary=summary)
            _finalize_tick_summary(
                db,
                job_row=job_row,
                summary=summary,
                step_errors=step_errors,
                fatal_error=None,
                overall_status="timeout_degraded",
            )
            return summary

        # 2b — Maintenance sessions swap LI.FI (expiration + réconciliation SUBMITTED)
        try:
            from services.lifi.swap_session_maintenance import run_swap_session_maintenance

            swap_maint = run_swap_session_maintenance(db, dry_run=dry_run)
            summary["swap_maintenance"] = swap_maint
            summary["steps"]["swap_maintenance"] = {
                "dry_run": dry_run,
                "expired": (swap_maint.get("expire_stale") or {}).get("swap_ids", []),
                "submitted_polled": (swap_maint.get("reconcile_submitted") or {}).get("polled", 0),
            }
        except Exception as exc:
            summary["swap_maintenance"] = {"error": str(exc)}
            summary["steps"]["swap_maintenance"] = {"error": str(exc)}
            step_errors.append("swap_maintenance_failed")
            logger.warning("defi_observability.swap_maintenance_failed", exc_info=True)

        # 2c — Outbox worker intent.created (Phase 2 S2b — flag OFF par défaut)
        try:
            from services.lifi.config import lifi_outbox_worker_enabled
            from services.transaction_outbox.worker import process_transaction_outbox_intent_created

            if lifi_outbox_worker_enabled() and not dry_run:
                outbox_step = process_transaction_outbox_intent_created(db, limit=20)
            else:
                outbox_step = {
                    "skipped": True,
                    "enabled": lifi_outbox_worker_enabled(),
                    "dry_run": dry_run,
                }
            summary["transaction_outbox"] = outbox_step
            summary["steps"]["transaction_outbox"] = outbox_step
        except Exception as exc:
            summary["transaction_outbox"] = {"error": str(exc)}
            summary["steps"]["transaction_outbox"] = {"error": str(exc)}
            step_errors.append("transaction_outbox_failed")
            logger.warning("defi_observability.transaction_outbox_failed", exc_info=True)

        # 2c-bis — Outbox worker intent.execute (signature déléguée serveur, flag OFF par défaut)
        try:
            from services.lifi.config import lifi_execution_worker_enabled
            from services.transaction_outbox.execution_worker import (
                process_transaction_outbox_intent_execute,
            )

            if lifi_execution_worker_enabled() and not dry_run:
                outbox_execute_step = process_transaction_outbox_intent_execute(db, limit=10)
            else:
                outbox_execute_step = {
                    "skipped": True,
                    "enabled": lifi_execution_worker_enabled(),
                    "dry_run": dry_run,
                }
            summary["transaction_outbox_intent_execute"] = outbox_execute_step
            summary["steps"]["transaction_outbox_intent_execute"] = outbox_execute_step
        except Exception as exc:
            summary["transaction_outbox_intent_execute"] = {"error": str(exc)}
            summary["steps"]["transaction_outbox_intent_execute"] = {"error": str(exc)}
            step_errors.append("transaction_outbox_intent_execute_failed")
            logger.warning(
                "defi_observability.transaction_outbox_intent_execute_failed",
                exc_info=True,
            )

        # 2d — Outbox worker intent.settle (Phase 2 S3a — settlement skeleton NOOP, flag OFF)
        try:
            from services.lifi.config import lifi_outbox_worker_enabled
            from services.transaction_outbox.settlement_worker import (
                process_transaction_outbox_intent_settle,
            )

            if lifi_outbox_worker_enabled() and not dry_run:
                outbox_settle_step = process_transaction_outbox_intent_settle(db, limit=20)
            else:
                outbox_settle_step = {
                    "skipped": True,
                    "enabled": lifi_outbox_worker_enabled(),
                    "dry_run": dry_run,
                }
            summary["transaction_outbox_intent_settle"] = outbox_settle_step
            summary["steps"]["transaction_outbox_intent_settle"] = outbox_settle_step
        except Exception as exc:
            summary["transaction_outbox_intent_settle"] = {"error": str(exc)}
            summary["steps"]["transaction_outbox_intent_settle"] = {"error": str(exc)}
            step_errors.append("transaction_outbox_intent_settle_failed")
            logger.warning(
                "defi_observability.transaction_outbox_intent_settle_failed",
                exc_info=True,
            )

        # 2e — Bundle V3 deposit outbox (bundle.v3_rebalance_requested — flag OFF par défaut)
        try:
            from services.portfolio_engine.bundles.bundle_v3_deposit_flow.config import (
                bundle_v3_deposit_worker_enabled,
            )
            from services.portfolio_engine.bundles.bundle_v3_deposit_flow.worker import (
                process_bundle_v3_deposit_outbox,
            )

            if bundle_v3_deposit_worker_enabled() and not dry_run:
                bundle_v3_deposit_step = process_bundle_v3_deposit_outbox(db, limit=10)
            else:
                bundle_v3_deposit_step = {
                    "skipped": True,
                    "enabled": bundle_v3_deposit_worker_enabled(),
                    "dry_run": dry_run,
                }
            summary["bundle_v3_deposit_outbox"] = bundle_v3_deposit_step
            summary["steps"]["bundle_v3_deposit_outbox"] = bundle_v3_deposit_step
        except Exception as exc:
            summary["bundle_v3_deposit_outbox"] = {"error": str(exc)}
            summary["steps"]["bundle_v3_deposit_outbox"] = {"error": str(exc)}
            step_errors.append("bundle_v3_deposit_outbox_failed")
            logger.warning(
                "defi_observability.bundle_v3_deposit_outbox_failed",
                exc_info=True,
            )

        # 2f — Reconcile-stale bundle portfolios (background — locks/intents/V3 zombies)
        try:
            from services.portfolio_engine.bundles.bundle_stale_reconcile_worker import (
                tick_bundle_stale_reconcile,
            )

            bundle_stale_step = tick_bundle_stale_reconcile(db, dry_run=dry_run)
            summary["bundle_stale_reconcile"] = bundle_stale_step
            summary["steps"]["bundle_stale_reconcile"] = {
                "enabled": bundle_stale_step.get("enabled"),
                "targets": bundle_stale_step.get("targets"),
                "reconciled": bundle_stale_step.get("reconciled"),
                "dead_letter_swept": bundle_stale_step.get("dead_letter_swept"),
                "errors": bundle_stale_step.get("errors"),
            }
        except Exception as exc:
            summary["bundle_stale_reconcile"] = {"error": str(exc)}
            summary["steps"]["bundle_stale_reconcile"] = {"error": str(exc)}
            step_errors.append("bundle_stale_reconcile_failed")
            logger.warning(
                "defi_observability.bundle_stale_reconcile_failed",
                exc_info=True,
            )

        if _timeout_before("user_reconcile"):
            summary["alerts"] = compute_ops_alerts(db, summary=summary)
            _finalize_tick_summary(
                db,
                job_row=job_row,
                summary=summary,
                step_errors=step_errors,
                fatal_error=None,
                overall_status="timeout_degraded",
            )
            return summary

        # 3 — Reconcile users actifs
        person_ids = list_recent_active_person_ids(db, hours=user_hours, limit=max_users)
        user_summaries: list[dict[str, Any]] = []
        total_anomalies = 0
        total_discrepancies_written = 0
        for person_id in person_ids:
            if _timeout_before(f"user_reconcile:{person_id}"):
                summary["users"] = {
                    "person_ids_scanned": [str(p) for p in person_ids],
                    "count": len(person_ids),
                    "partial": True,
                    "reports": user_summaries,
                }
                summary["alerts"] = compute_ops_alerts(db, summary=summary)
                _finalize_tick_summary(
                    db,
                    job_row=job_row,
                    summary=summary,
                    step_errors=step_errors,
                    fatal_error=None,
                    overall_status="timeout_degraded",
                )
                return summary
            try:
                report = build_user_reconcile_report(
                    db,
                    person_id=person_id,
                    dry_run=dry_run,
                    persist_discrepancies=not dry_run,
                    chain_id=CHAIN_BASE,
                )
                total_anomalies += len(report.anomalies)
                total_discrepancies_written += report.discrepancies_written
                user_summaries.append(
                    {
                        "person_id": str(person_id),
                        "anomaly_count": len(report.anomalies),
                        "discrepancies_written": report.discrepancies_written,
                        "warnings": report.warnings,
                    }
                )
            except Exception as exc:
                user_summaries.append(
                    {"person_id": str(person_id), "error": str(exc)},
                )
                step_errors.append(f"user_reconcile_failed:{person_id}")

        summary["users"] = {
            "person_ids_scanned": [str(p) for p in person_ids],
            "count": len(person_ids),
            "total_anomalies": total_anomalies,
            "total_discrepancies_written": total_discrepancies_written if not dry_run else 0,
            "reports": user_summaries,
        }
        summary["steps"]["user_reconcile"] = {
            "users": len(person_ids),
            "dry_run": dry_run,
            "persist_discrepancies": not dry_run,
        }

        summary["alerts"] = compute_ops_alerts(db, summary=summary)
        overall = _overall_status(
            fatal_error=fatal_error,
            step_errors=step_errors,
            alerts=summary["alerts"],
        )
        _finalize_tick_summary(
            db,
            job_row=job_row,
            summary=summary,
            step_errors=step_errors,
            fatal_error=fatal_error,
            overall_status=overall,
        )

    except Exception as exc:
        fatal_error = str(exc)
        summary["overall_status"] = "error"
        summary["fatal_error"] = fatal_error
        if job_row is not None:
            DefiJobRunRepository.finish(
                db,
                job_row,
                status="error",
                summary_json=summary,
                error_json={"traceback": traceback.format_exc()},
            )
            summary["job_run_id"] = str(job_row.id)
        raise

    return summary
