"""Exécution séquentielle ou parallèle des quotes d'allocation bundle (Phase 5A)."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.security.context import ActorContext

from .allocation_config import BUNDLE_ALLOC_MAX_PARALLEL_LEGS
from .allocation_observability import log_allocation_event
from .allocation_planner import PlannedAllocationLeg

if TYPE_CHECKING:
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class AllocationLegRunStats:
    succeeded: int = 0
    failed: int = 0
    pending: int = 0
    total_entry_consumed: Decimal = Decimal("0")
    cash_available: Decimal = Decimal("0")


def _record_from_result(
    planned: PlannedAllocationLeg,
    exec_result: dict,
    stats: AllocationLegRunStats,
) -> dict:
    status = exec_result.get("status")
    if status == "pending":
        stats.pending += 1
        return exec_result["record"]
    if status == "completed":
        stats.succeeded += 1
        stats.total_entry_consumed += planned.alloc_entry_amount
        stats.cash_available -= planned.alloc_entry_amount
        return exec_result["record"]
    stats.failed += 1
    return exec_result.get("record") or {
        "asset": planned.lifi_target,
        "instrument_id": str(planned.target_instrument_id),
        "target_weight": float(planned.target_weight),
        "status": "failed",
        "error": exec_result.get("error", "unknown"),
    }


def _failed_record(planned: PlannedAllocationLeg, exc: Exception) -> dict:
    return {
        "asset": planned.lifi_target,
        "instrument_id": str(planned.target_instrument_id),
        "target_weight": float(planned.target_weight),
        "entry_asset_consumed": 0,
        "crypto_received": 0,
        "status": "failed",
        "error": str(exc),
    }


def run_allocation_legs_sequential(
    orchestrator: BundleOrchestrator,
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    entry_asset: str,
    entry_instrument_id: UUID,
    batch_id: str,
    actor: ActorContext,
    planned_legs: list[PlannedAllocationLeg],
    initial_cash_available: Decimal,
    execution_asset_from_planned: bool = False,
) -> tuple[list[dict], AllocationLegRunStats]:
    stats = AllocationLegRunStats(cash_available=initial_cash_available)
    alloc_results: list[dict] = []

    for planned in planned_legs:
        if planned.alloc_entry_amount > stats.cash_available:
            continue
        leg_asset = planned.lifi_target if execution_asset_from_planned else planned.target_asset
        started = time.monotonic()
        log_allocation_event(
            "quote_started",
            portfolio_id=str(portfolio_id),
            batch_id=batch_id,
            leg_id=planned.ext_ref,
            asset=leg_asset,
            parallel_enabled=False,
        )
        try:
            exec_result = orchestrator._run_allocation_leg(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument_id,
                target_asset=leg_asset,
                target_instrument_id=planned.target_instrument_id,
                alloc_entry_amount=planned.alloc_entry_amount,
                ext_ref=planned.ext_ref,
                batch_id=batch_id,
                actor=actor,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            log_allocation_event(
                "quote_completed",
                portfolio_id=str(portfolio_id),
                batch_id=batch_id,
                leg_id=planned.ext_ref,
                asset=leg_asset,
                leg_status=exec_result.get("status"),
                parallel_enabled=False,
                duration_ms=duration_ms,
            )
            alloc_results.append(_record_from_result(planned, exec_result, stats))
        except Exception as exc:
            stats.failed += 1
            logger.warning(
                "Bundle allocation leg failed: asset=%s err=%s",
                leg_asset,
                exc,
            )
            alloc_results.append(_failed_record(planned, exc))

    return alloc_results, stats


@dataclass(frozen=True)
class _ParallelLegJob:
    index: int
    planned: PlannedAllocationLeg
    client_id: UUID
    portfolio_id: UUID
    entry_asset: str
    entry_instrument_id: UUID
    batch_id: str
    actor_type: str
    actor_id: str


def _run_parallel_leg_job(job: _ParallelLegJob) -> tuple[int, dict[str, Any]]:
    from database import SessionLocal
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    started = time.monotonic()
    log_allocation_event(
        "quote_started",
        portfolio_id=str(job.portfolio_id),
        batch_id=job.batch_id,
        leg_id=job.planned.ext_ref,
        asset=job.planned.lifi_target,
        parallel_enabled=True,
    )
    db = SessionLocal()
    try:
        orchestrator = BundleOrchestrator()
        actor = ActorContext(actor_type=job.actor_type, actor_id=job.actor_id)
        exec_result = orchestrator._run_allocation_leg(
            db,
            client_id=job.client_id,
            portfolio_id=job.portfolio_id,
            entry_asset=job.entry_asset,
            entry_instrument_id=job.entry_instrument_id,
            target_asset=job.planned.lifi_target,
            target_instrument_id=job.planned.target_instrument_id,
            alloc_entry_amount=job.planned.alloc_entry_amount,
            ext_ref=job.planned.ext_ref,
            batch_id=job.batch_id,
            actor=actor,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        log_allocation_event(
            "quote_completed",
            portfolio_id=str(job.portfolio_id),
            batch_id=job.batch_id,
            leg_id=job.planned.ext_ref,
            asset=job.planned.lifi_target,
            leg_status=exec_result.get("status"),
            parallel_enabled=True,
            duration_ms=duration_ms,
        )
        return job.index, exec_result
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        log_allocation_event(
            "quote_completed",
            portfolio_id=str(job.portfolio_id),
            batch_id=job.batch_id,
            leg_id=job.planned.ext_ref,
            asset=job.planned.lifi_target,
            leg_status="failed",
            parallel_enabled=True,
            duration_ms=duration_ms,
            error=str(exc),
        )
        return job.index, {"status": "failed", "error": str(exc)}
    finally:
        db.close()


def run_allocation_legs_parallel(
    orchestrator: BundleOrchestrator,
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    entry_asset: str,
    entry_instrument_id: UUID,
    batch_id: str,
    actor: ActorContext,
    planned_legs: list[PlannedAllocationLeg],
    initial_cash_available: Decimal,
    person_id: str | None = None,
    fund_amount: Decimal | None = None,
    buffer_amount: Decimal | None = None,
    allocatable_amount: Decimal | None = None,
) -> tuple[list[dict], AllocationLegRunStats]:
    """Quotes LI.FI en parallèle — commit du fund requis avant appel."""
    if not planned_legs:
        return [], AllocationLegRunStats(cash_available=initial_cash_available)

    batch_started = time.monotonic()
    parallel_failed = False

    try:
        db.commit()

        stats = AllocationLegRunStats(cash_available=initial_cash_available)
        workers = min(BUNDLE_ALLOC_MAX_PARALLEL_LEGS, len(planned_legs))
        jobs = [
            _ParallelLegJob(
                index=i,
                planned=planned,
                client_id=client_id,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument_id,
                batch_id=batch_id,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
            )
            for i, planned in enumerate(planned_legs)
        ]

        results_by_index: dict[int, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run_parallel_leg_job, job) for job in jobs]
            for future in as_completed(futures):
                index, exec_result = future.result()
                results_by_index[index] = exec_result

        alloc_results: list[dict] = []
        for i, planned in enumerate(planned_legs):
            exec_result = results_by_index.get(i, {"status": "failed", "error": "missing_result"})
            if exec_result.get("status") == "failed" and "record" not in exec_result:
                parallel_failed = True
                stats.failed += 1
                alloc_results.append(_failed_record(planned, Exception(str(exec_result.get("error")))))
            else:
                alloc_results.append(_record_from_result(planned, exec_result, stats))

        duration_ms = int((time.monotonic() - batch_started) * 1000)
        log_allocation_event(
            "parallel_batch_completed",
            person_id=person_id,
            portfolio_id=str(portfolio_id),
            batch_id=batch_id,
            fund_amount=float(fund_amount) if fund_amount is not None else None,
            buffer_amount=float(buffer_amount) if buffer_amount is not None else None,
            allocatable_amount=float(allocatable_amount) if allocatable_amount is not None else None,
            legs_count=len(planned_legs),
            parallel_enabled=True,
            duration_ms=duration_ms,
            legs_succeeded=stats.succeeded,
            legs_failed=stats.failed,
            legs_pending=stats.pending,
            fallback_to_sequential=False,
        )

        if parallel_failed and stats.pending == 0 and stats.succeeded == 0:
            log_allocation_event(
                "parallel_batch_completed",
                person_id=person_id,
                portfolio_id=str(portfolio_id),
                batch_id=batch_id,
                legs_count=len(planned_legs),
                parallel_enabled=False,
                fallback_to_sequential=True,
                reason="parallel_all_failed",
            )
            return run_allocation_legs_sequential(
                orchestrator,
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument_id,
                batch_id=batch_id,
                actor=actor,
                planned_legs=planned_legs,
                initial_cash_available=initial_cash_available,
                execution_asset_from_planned=True,
            )

        db.expire_all()
        return alloc_results, stats
    except Exception as exc:
        duration_ms = int((time.monotonic() - batch_started) * 1000)
        log_allocation_event(
            "parallel_batch_completed",
            person_id=person_id,
            portfolio_id=str(portfolio_id),
            batch_id=batch_id,
            legs_count=len(planned_legs),
            parallel_enabled=True,
            duration_ms=duration_ms,
            fallback_to_sequential=True,
            error=str(exc),
        )
        logger.warning("Parallel allocation batch failed, fallback sequential: %s", exc)
        return run_allocation_legs_sequential(
            orchestrator,
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            entry_asset=entry_asset,
            entry_instrument_id=entry_instrument_id,
            batch_id=batch_id,
            actor=actor,
            planned_legs=planned_legs,
            initial_cash_available=initial_cash_available,
            execution_asset_from_planned=True,
        )
