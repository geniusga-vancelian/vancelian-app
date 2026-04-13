"""Admin endpoints for scheduler / scheduled jobs (Hardening Subphase 4)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from ..security.context import ActorContext
from ..security.dependencies import require_admin_or_ops
from .repository import ScheduledJobRepository
from .schemas import (
    ScheduledJobCreate,
    ScheduledJobListResponse,
    ScheduledJobRead,
    ScheduledJobUpdate,
    SchedulerRunSummary,
)
from .service import (
    ScheduledJobConfigError,
    ScheduledJobNotFoundError,
    SchedulerService,
)

router = APIRouter()
_service = SchedulerService()
_repo = ScheduledJobRepository()
_guard = require_admin_or_ops()


# ------------------------------------------------------------------
# CRUD-lite
# ------------------------------------------------------------------

@router.get("/scheduled-jobs", response_model=ScheduledJobListResponse)
def list_scheduled_jobs(
    job_type: Optional[str] = Query(None),
    is_enabled: Optional[bool] = Query(None),
    scope_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _repo.list_jobs(
        db, job_type=job_type, is_enabled=is_enabled, scope_type=scope_type,
        skip=skip, limit=limit,
    )
    return ScheduledJobListResponse(
        items=[ScheduledJobRead.model_validate(j) for j in items],
        total=total,
    )


@router.post("/scheduled-jobs", response_model=ScheduledJobRead, status_code=201)
def create_scheduled_job(
    body: ScheduledJobCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        job = _service.register_scheduled_job(
            db,
            job_name=body.job_name,
            job_type=body.job_type,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            schedule_type=body.schedule_type,
            cron_expression=body.cron_expression,
            interval_seconds=body.interval_seconds,
            is_enabled=body.is_enabled,
            metadata=body.metadata,
        )
        db.commit()
        db.refresh(job)
        return ScheduledJobRead.model_validate(job)
    except ScheduledJobConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/scheduled-jobs/{job_id}", response_model=ScheduledJobRead)
def get_scheduled_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        job = _service.get_scheduled_job(db, job_id)
        return ScheduledJobRead.model_validate(job)
    except ScheduledJobNotFoundError:
        raise HTTPException(status_code=404, detail=f"ScheduledJob {job_id} not found")


@router.patch("/scheduled-jobs/{job_id}", response_model=ScheduledJobRead)
def update_scheduled_job(
    job_id: UUID,
    body: ScheduledJobUpdate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        job = _service.update_scheduled_job(
            db,
            job_id,
            is_enabled=body.is_enabled,
            cron_expression=body.cron_expression,
            interval_seconds=body.interval_seconds,
            next_run_at=body.next_run_at,
            metadata=body.metadata,
        )
        db.commit()
        db.refresh(job)
        return ScheduledJobRead.model_validate(job)
    except ScheduledJobNotFoundError:
        raise HTTPException(status_code=404, detail=f"ScheduledJob {job_id} not found")


# ------------------------------------------------------------------
# Execution
# ------------------------------------------------------------------

@router.post("/scheduled-jobs/run-due", response_model=SchedulerRunSummary)
def run_due_jobs(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    summary = _service.run_due_jobs(db)
    db.commit()
    return summary


@router.post("/scheduled-jobs/{job_id}/run")
def run_single_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _service.run_job_by_id(db, job_id)
        db.commit()
        return result
    except ScheduledJobNotFoundError:
        raise HTTPException(status_code=404, detail=f"ScheduledJob {job_id} not found")
