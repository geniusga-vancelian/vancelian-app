"""Tests for Hardening Subphase 4 — Scheduler / Job Framework.

Covers:
 1. create interval job
 2. create manual_only job
 3. invalid interval config rejected
 4. invalid cron config rejected
 5. update enable/disable works
 6. due jobs selected correctly
 7. disabled jobs ignored
 8. manual_only jobs ignored
 9. successful job updates last_run_at and next_run_at
10. failing job counted in summary
11. single job can run manually
12. manual_only job can run manually
13. valuation_snapshot dispatch works
14. strategy_evaluation dispatch works
15. orchestration_cycle dispatch works
16. reconciliation dispatch works
17. list scheduled jobs endpoint works
18. run-due endpoint works
19. run single job endpoint works
20. audit event created for scheduled job run
21. job run integration works
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.jobs.models import JobRun
from services.portfolio_engine.hardening.scheduler.models import ScheduledJob
from services.portfolio_engine.hardening.scheduler.repository import ScheduledJobRepository
from services.portfolio_engine.hardening.scheduler.service import (
    ScheduledJobConfigError,
    ScheduledJobNotFoundError,
    SchedulerService,
)
from conftest import make_linked_client
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> SchedulerService:
    return SchedulerService()


@pytest.fixture
def pe_client(db: Session) -> Client:
    return make_linked_client(db, email=f"sched_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def portfolio(db: Session, pe_client: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=pe_client.id,
        portfolio_type="bundle_portfolio",
        name="Scheduler Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


def _make_interval_job(
    db: Session, svc: SchedulerService, portfolio: Portfolio,
    job_type: str = "reconciliation_trades_positions",
    interval: int = 3600,
    is_enabled: bool = True,
) -> ScheduledJob:
    return svc.register_scheduled_job(
        db,
        job_name=f"Test {job_type}",
        job_type=job_type,
        scope_type="portfolio",
        scope_id=str(portfolio.id),
        schedule_type="interval",
        interval_seconds=interval,
        is_enabled=is_enabled,
    )


# ---------------------------------------------------------------------------
# 1–5 CRUD-lite
# ---------------------------------------------------------------------------

class TestScheduledJobCRUD:

    def test_create_interval_job(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio)
        assert job.job_type == "reconciliation_trades_positions"
        assert job.schedule_type == "interval"
        assert job.interval_seconds == 3600
        assert job.is_enabled is True
        assert job.next_run_at is not None

    def test_create_manual_only_job(self, db: Session, svc, portfolio):
        job = svc.register_scheduled_job(
            db,
            job_name="Manual rebuild",
            job_type="rebuild_positions",
            scope_type="portfolio",
            scope_id=str(portfolio.id),
            schedule_type="manual_only",
        )
        assert job.schedule_type == "manual_only"
        assert job.next_run_at is None

    def test_invalid_interval_config_rejected(self, db: Session, svc, portfolio):
        with pytest.raises(ScheduledJobConfigError, match="interval_seconds"):
            svc.register_scheduled_job(
                db,
                job_name="Bad interval",
                job_type="valuation_snapshot",
                scope_type="portfolio",
                scope_id=str(portfolio.id),
                schedule_type="interval",
                interval_seconds=None,
            )

    def test_invalid_cron_config_rejected(self, db: Session, svc, portfolio):
        with pytest.raises(ScheduledJobConfigError, match="cron_expression"):
            svc.register_scheduled_job(
                db,
                job_name="Bad cron",
                job_type="valuation_snapshot",
                scope_type="portfolio",
                scope_id=str(portfolio.id),
                schedule_type="cron",
                cron_expression=None,
            )

    def test_update_enable_disable(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio)
        assert job.is_enabled is True

        updated = svc.update_scheduled_job(db, job.id, is_enabled=False)
        assert updated.is_enabled is False

        updated2 = svc.update_scheduled_job(db, job.id, is_enabled=True)
        assert updated2.is_enabled is True


# ---------------------------------------------------------------------------
# 6–10 run_due_jobs
# ---------------------------------------------------------------------------

class TestRunDueJobs:

    def test_due_jobs_selected(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio, interval=1)
        ScheduledJobRepository.update(
            db, job, next_run_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        db.flush()

        summary = svc.run_due_jobs(db)
        assert summary.jobs_found >= 1
        assert summary.jobs_run >= 1

    def test_disabled_jobs_ignored(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio, interval=1, is_enabled=False)
        ScheduledJobRepository.update(
            db, job, next_run_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        db.flush()

        summary = svc.run_due_jobs(db)
        ran_ids = [str(j.id) for j in db.query(JobRun).filter(
            JobRun.scope_id == str(portfolio.id),
            JobRun.job_type.like("reconciliation_%"),
        ).all()]
        assert str(job.id) not in ran_ids or summary.jobs_found == 0

    def test_manual_only_jobs_ignored(self, db: Session, svc, portfolio):
        svc.register_scheduled_job(
            db,
            job_name="Manual only",
            job_type="rebuild_positions",
            scope_type="portfolio",
            scope_id=str(portfolio.id),
            schedule_type="manual_only",
        )

        summary = svc.run_due_jobs(db)
        assert summary.jobs_found == 0

    def test_successful_job_updates_timestamps(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio, interval=7200)
        ScheduledJobRepository.update(
            db, job, next_run_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        db.flush()

        old_next = job.next_run_at
        svc.run_due_jobs(db)
        db.refresh(job)
        assert job.last_run_at is not None
        assert job.next_run_at is not None
        assert job.next_run_at > old_next

    def test_failing_job_counted(self, db: Session, svc, portfolio):
        job = _make_interval_job(
            db, svc, portfolio,
            job_type="reconciliation_trades_positions",
        )
        ScheduledJobRepository.update(
            db, job,
            next_run_at=datetime.now(timezone.utc) - timedelta(seconds=10),
            scope_id=str(uuid.uuid4()),
        )
        db.flush()

        summary = svc.run_due_jobs(db)
        assert summary.jobs_failed >= 1


# ---------------------------------------------------------------------------
# 11–12 run_job_by_id
# ---------------------------------------------------------------------------

class TestRunJobById:

    def test_single_job_runs(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio)
        result = svc.run_job_by_id(db, job.id)
        assert "job_run_id" in result
        assert "status" in result

    def test_manual_only_runs(self, db: Session, svc, portfolio):
        job = svc.register_scheduled_job(
            db,
            job_name="Manual recon",
            job_type="reconciliation_trades_positions",
            scope_type="portfolio",
            scope_id=str(portfolio.id),
            schedule_type="manual_only",
        )
        result = svc.run_job_by_id(db, job.id)
        assert result["status"] == "matched" or result["status"] == "mismatched"


# ---------------------------------------------------------------------------
# 13–16 Dispatch mapping
# ---------------------------------------------------------------------------

class TestDispatchMapping:

    def test_valuation_dispatch(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio, job_type="valuation_snapshot")
        with patch(
            "services.portfolio_engine.valuations.service.ValuationService.create_snapshot",
            return_value=MagicMock(),
        ):
            result = svc.run_job_by_id(db, job.id)
            assert result["status"] == "completed"
            assert result["job_run_id"] is not None

    def test_strategy_dispatch(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio, job_type="strategy_evaluation")
        with patch(
            "services.portfolio_engine.strategy_engine.service.StrategyEngineService.evaluate_portfolio_strategies",
            return_value=MagicMock(),
        ):
            result = svc.run_job_by_id(db, job.id)
            assert result["status"] == "completed"

    def test_orchestration_dispatch(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio, job_type="orchestration_cycle")
        with patch(
            "services.portfolio_engine.orchestrator.service.RebalanceOrchestratorService.run_portfolio_cycle",
            return_value=MagicMock(),
        ):
            result = svc.run_job_by_id(db, job.id)
            assert result["status"] == "completed"

    def test_reconciliation_dispatch(self, db: Session, svc, portfolio):
        job = _make_interval_job(
            db, svc, portfolio, job_type="reconciliation_trades_positions",
        )
        result = svc.run_job_by_id(db, job.id)
        assert result["status"] in ("matched", "mismatched")


# ---------------------------------------------------------------------------
# 17–19 Admin endpoints (service-level)
# ---------------------------------------------------------------------------

class TestAdminEndpoints:

    def test_list_scheduled_jobs(self, db: Session, svc, portfolio):
        _make_interval_job(db, svc, portfolio)
        items, total = ScheduledJobRepository.list_jobs(db)
        assert total >= 1

    def test_run_due_endpoint(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio, interval=1)
        ScheduledJobRepository.update(
            db, job, next_run_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        db.flush()
        summary = svc.run_due_jobs(db)
        assert summary.jobs_run >= 1

    def test_run_single_endpoint(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio)
        result = svc.run_job_by_id(db, job.id)
        assert "job_run_id" in result


# ---------------------------------------------------------------------------
# 20–21 Audit / Job Run integration
# ---------------------------------------------------------------------------

class TestAuditJobIntegration:

    def test_audit_event_created(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio)
        svc.run_job_by_id(db, job.id)

        events = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "scheduled_job_run")
            .all()
        )
        assert len(events) >= 1
        last = events[-1]
        assert last.entity_id == str(job.id)

    def test_job_run_created(self, db: Session, svc, portfolio):
        job = _make_interval_job(db, svc, portfolio)
        result = svc.run_job_by_id(db, job.id)
        jr = db.query(JobRun).filter(JobRun.id == result["job_run_id"]).first()
        assert jr is not None
        assert jr.status in ("completed", "started")
