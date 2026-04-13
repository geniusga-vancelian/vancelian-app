"""Scheduler / Job Framework Service (Hardening Subphase 4).

Orchestrates existing services via scheduled job definitions stored in pe_scheduled_jobs.
Does NOT implement business logic — only dispatches to existing services.

Job run integration strategy:
  - ReconciliationService and RebuildService create their own pe_job_runs internally
    → scheduler extracts job_run_id from their result objects.
  - ValuationService, StrategyEngineService, RebalanceOrchestratorService do NOT create
    pe_job_runs → scheduler wraps these in an outer job run.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..audit_service import AuditService
from ..jobs.models import JobRun
from ..jobs.repository import JobRunRepository
from .models import ScheduledJob
from .repository import ScheduledJobRepository
from .schemas import SchedulerRunSummary

logger = logging.getLogger(__name__)

VALID_JOB_TYPES = {
    "valuation_snapshot",
    "strategy_evaluation",
    "orchestration_cycle",
    "reconciliation_trades_positions",
    "reconciliation_positions_valuations",
    "reconciliation_valuations_performance",
    "reconciliation_ledger_balances",
    "rebuild_positions",
    "rebuild_valuations",
    "rebuild_performance",
}

VALID_SCHEDULE_TYPES = {"interval", "cron", "manual_only"}

_JOB_REQUIRES_PORTFOLIO = VALID_JOB_TYPES - {"reconciliation_ledger_balances"}

_job_repo = JobRunRepository()
_sched_repo = ScheduledJobRepository()
_audit = AuditService()


class ScheduledJobConfigError(Exception):
    """Invalid scheduled job configuration."""


class ScheduledJobNotFoundError(Exception):
    def __init__(self, job_id: UUID):
        self.job_id = job_id
        super().__init__(f"ScheduledJob {job_id} not found")


class SchedulerService:

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    def register_scheduled_job(
        self,
        db: Session,
        *,
        job_name: str,
        job_type: str,
        scope_type: str,
        scope_id: Optional[str] = None,
        schedule_type: str = "interval",
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        is_enabled: bool = True,
        metadata: Optional[dict] = None,
    ) -> ScheduledJob:
        self._validate_config(
            job_type=job_type,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            scope_type=scope_type,
            scope_id=scope_id,
        )

        now = datetime.now(timezone.utc)
        next_run = self._compute_initial_next_run(now, schedule_type, interval_seconds, cron_expression)

        job = _sched_repo.create(db, data={
            "job_name": job_name,
            "job_type": job_type,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "schedule_type": schedule_type,
            "cron_expression": cron_expression,
            "interval_seconds": interval_seconds,
            "is_enabled": is_enabled,
            "next_run_at": next_run,
            "metadata_": metadata or {},
        })

        _audit.log_success(
            db,
            entity_type="scheduled_job",
            entity_id=str(job.id),
            action="scheduled_job_created",
            metadata={"job_type": job_type, "schedule_type": schedule_type},
        )
        return job

    def update_scheduled_job(
        self,
        db: Session,
        job_id: UUID,
        *,
        is_enabled: Optional[bool] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        next_run_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> ScheduledJob:
        job = _sched_repo.get_by_id(db, job_id)
        if job is None:
            raise ScheduledJobNotFoundError(job_id)

        updates = {}
        if is_enabled is not None:
            updates["is_enabled"] = is_enabled
        if cron_expression is not None:
            updates["cron_expression"] = cron_expression
        if interval_seconds is not None:
            updates["interval_seconds"] = interval_seconds
        if next_run_at is not None:
            updates["next_run_at"] = next_run_at
        if metadata is not None:
            updates["metadata_"] = metadata

        if updates:
            job = _sched_repo.update(db, job, **updates)
            _audit.log_success(
                db,
                entity_type="scheduled_job",
                entity_id=str(job.id),
                action="scheduled_job_updated",
                metadata={"updated_fields": list(updates.keys())},
            )
        return job

    def get_scheduled_job(self, db: Session, job_id: UUID) -> ScheduledJob:
        job = _sched_repo.get_by_id(db, job_id)
        if job is None:
            raise ScheduledJobNotFoundError(job_id)
        return job

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_due_jobs(self, db: Session) -> SchedulerRunSummary:
        now = datetime.now(timezone.utc)
        due_jobs = _sched_repo.list_due(db, now=now)

        summary = SchedulerRunSummary(
            jobs_found=len(due_jobs), jobs_run=0, jobs_succeeded=0, jobs_failed=0,
        )

        for sj in due_jobs:
            summary.jobs_run += 1
            try:
                self._dispatch_and_record(db, sj, now)
                summary.jobs_succeeded += 1
            except Exception as exc:
                summary.jobs_failed += 1
                summary.warnings.append(f"{sj.job_name} ({sj.id}): {exc}")
                logger.exception("Scheduled job %s failed", sj.id)

        _audit.log_success(
            db,
            entity_type="scheduler",
            entity_id=None,
            action="scheduled_jobs_run_due",
            metadata={
                "jobs_found": summary.jobs_found,
                "jobs_run": summary.jobs_run,
                "jobs_succeeded": summary.jobs_succeeded,
                "jobs_failed": summary.jobs_failed,
            },
        )
        return summary

    def run_job_by_id(self, db: Session, job_id: UUID) -> dict:
        sj = _sched_repo.get_by_id(db, job_id)
        if sj is None:
            raise ScheduledJobNotFoundError(job_id)

        now = datetime.now(timezone.utc)
        return self._dispatch_and_record(db, sj, now)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch_and_record(self, db: Session, sj: ScheduledJob, now: datetime) -> dict:
        result = self._dispatch_job(db, sj)

        _sched_repo.update(
            db,
            sj,
            last_run_at=now,
            next_run_at=self.compute_next_run_at(sj, now),
        )

        job_run_id = result.get("job_run_id")
        _audit.log_success(
            db,
            entity_type="scheduled_job",
            entity_id=str(sj.id),
            action="scheduled_job_run",
            metadata={
                "job_type": sj.job_type,
                "scope_type": sj.scope_type,
                "scope_id": sj.scope_id,
                "job_run_id": str(job_run_id) if job_run_id else None,
            },
        )
        return result

    def _dispatch_job(self, db: Session, sj: ScheduledJob) -> dict:
        jt = sj.job_type
        pid = UUID(sj.scope_id) if sj.scope_id else None

        if jt == "valuation_snapshot":
            return self._dispatch_valuation(db, sj, pid)
        elif jt == "strategy_evaluation":
            return self._dispatch_strategy(db, sj, pid)
        elif jt == "orchestration_cycle":
            return self._dispatch_orchestration(db, sj, pid)
        elif jt.startswith("reconciliation_"):
            return self._dispatch_reconciliation(db, sj, pid)
        elif jt.startswith("rebuild_"):
            return self._dispatch_rebuild(db, sj, pid)
        else:
            raise ValueError(f"Unknown job_type: {jt}")

    # ---- valuation (wraps in job run) ----

    def _dispatch_valuation(self, db: Session, sj: ScheduledJob, portfolio_id: UUID) -> dict:
        from ...valuations.service import ValuationService

        job_run = _job_repo.create(db, data={
            "job_type": f"scheduled_{sj.job_type}",
            "scope_type": sj.scope_type,
            "scope_id": sj.scope_id,
            "status": "started",
            "started_at": datetime.now(timezone.utc),
        })
        db.flush()

        try:
            svc = ValuationService()
            svc.create_snapshot(db, portfolio_id, source="scheduled_snapshot")
            _job_repo.mark_completed(db, job_run)
            return {"job_run_id": job_run.id, "status": "completed"}
        except Exception:
            _job_repo.mark_failed(db, job_run, error_message="valuation dispatch failed")
            raise

    # ---- strategy (wraps in job run) ----

    def _dispatch_strategy(self, db: Session, sj: ScheduledJob, portfolio_id: UUID) -> dict:
        from ...strategy_engine.service import StrategyEngineService

        job_run = _job_repo.create(db, data={
            "job_type": f"scheduled_{sj.job_type}",
            "scope_type": sj.scope_type,
            "scope_id": sj.scope_id,
            "status": "started",
            "started_at": datetime.now(timezone.utc),
        })
        db.flush()

        try:
            svc = StrategyEngineService()
            svc.evaluate_portfolio_strategies(db, portfolio_id)
            _job_repo.mark_completed(db, job_run)
            return {"job_run_id": job_run.id, "status": "completed"}
        except Exception:
            _job_repo.mark_failed(db, job_run, error_message="strategy dispatch failed")
            raise

    # ---- orchestration (wraps in job run) ----

    def _dispatch_orchestration(self, db: Session, sj: ScheduledJob, portfolio_id: UUID) -> dict:
        from ...orchestrator.service import RebalanceOrchestratorService

        job_run = _job_repo.create(db, data={
            "job_type": f"scheduled_{sj.job_type}",
            "scope_type": sj.scope_type,
            "scope_id": sj.scope_id,
            "status": "started",
            "started_at": datetime.now(timezone.utc),
        })
        db.flush()

        try:
            svc = RebalanceOrchestratorService()
            svc.run_portfolio_cycle(db, portfolio_id)
            _job_repo.mark_completed(db, job_run)
            return {"job_run_id": job_run.id, "status": "completed"}
        except Exception:
            _job_repo.mark_failed(db, job_run, error_message="orchestration dispatch failed")
            raise

    # ---- reconciliation (already creates job runs) ----

    _RECON_TYPE_MAP = {
        "reconciliation_trades_positions": "trades_vs_positions",
        "reconciliation_positions_valuations": "positions_vs_valuations",
        "reconciliation_valuations_performance": "valuations_vs_performance",
        "reconciliation_ledger_balances": "ledger_entries_vs_balances",
    }

    def _dispatch_reconciliation(self, db: Session, sj: ScheduledJob, portfolio_id: Optional[UUID]) -> dict:
        from ..reconciliation.service import ReconciliationService

        recon_type = self._RECON_TYPE_MAP[sj.job_type]
        svc = ReconciliationService()
        result = svc.run_reconciliation_job(
            db, reconciliation_type=recon_type, portfolio_id=portfolio_id,
        )
        return {"job_run_id": result.job_run_id, "status": result.status}

    # ---- rebuild (already creates job runs) ----

    def _dispatch_rebuild(self, db: Session, sj: ScheduledJob, portfolio_id: UUID) -> dict:
        from ..jobs.service import RebuildService

        svc = RebuildService()
        result = svc.run_rebuild_job(db, job_type=sj.job_type, portfolio_id=portfolio_id)
        return {"job_run_id": result.job_run_id, "status": result.status}

    # ------------------------------------------------------------------
    # Next-run computation
    # ------------------------------------------------------------------

    def compute_next_run_at(
        self, sj: ScheduledJob, reference: datetime,
    ) -> Optional[datetime]:
        if sj.schedule_type == "manual_only":
            return None
        if sj.schedule_type == "interval" and sj.interval_seconds:
            return reference + timedelta(seconds=sj.interval_seconds)
        if sj.schedule_type == "cron" and sj.cron_expression:
            return self._next_cron(sj.cron_expression, reference)
        return None

    @staticmethod
    def _compute_initial_next_run(
        now: datetime,
        schedule_type: str,
        interval_seconds: Optional[int],
        cron_expression: Optional[str],
    ) -> Optional[datetime]:
        if schedule_type == "manual_only":
            return None
        if schedule_type == "interval" and interval_seconds:
            return now + timedelta(seconds=interval_seconds)
        if schedule_type == "cron" and cron_expression:
            return SchedulerService._next_cron(cron_expression, now)
        return None

    @staticmethod
    def _next_cron(expression: str, reference: datetime) -> Optional[datetime]:
        """Compute next cron occurrence. Uses croniter if available, otherwise returns None."""
        try:
            from croniter import croniter
            cron = croniter(expression, reference)
            return cron.get_next(datetime)
        except ImportError:
            logger.warning("croniter not installed — cron schedule next_run_at cannot be computed")
            return None
        except Exception:
            logger.warning("Invalid cron expression: %s", expression)
            return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_config(
        *,
        job_type: str,
        schedule_type: str,
        cron_expression: Optional[str],
        interval_seconds: Optional[int],
        scope_type: str,
        scope_id: Optional[str],
    ) -> None:
        if job_type not in VALID_JOB_TYPES:
            raise ScheduledJobConfigError(f"Invalid job_type: {job_type}")
        if schedule_type not in VALID_SCHEDULE_TYPES:
            raise ScheduledJobConfigError(f"Invalid schedule_type: {schedule_type}")
        if schedule_type == "interval" and not interval_seconds:
            raise ScheduledJobConfigError("interval schedule requires interval_seconds")
        if schedule_type == "cron" and not cron_expression:
            raise ScheduledJobConfigError("cron schedule requires cron_expression")
        if job_type in _JOB_REQUIRES_PORTFOLIO and not scope_id:
            raise ScheduledJobConfigError(f"job_type {job_type} requires scope_id (portfolio_id)")
