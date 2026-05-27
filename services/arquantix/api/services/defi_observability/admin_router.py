"""Router admin — historique defi_observability_job_runs (jobs uniquement)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

from .admin_service import get_job_run_admin, list_job_runs_admin
from .schemas import DefiJobRunListResponse, DefiJobRunSummary

defi_observability_admin_router = APIRouter(
    prefix="/api/admin/onchain-reconciliation",
    tags=["defi-observability-admin"],
)
_guard = require_admin_or_ops()


@defi_observability_admin_router.get("/jobs", response_model=DefiJobRunListResponse)
def list_defi_observability_jobs(
    job_name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    items, total = list_job_runs_admin(db, job_name=job_name, skip=skip, limit=limit)
    return DefiJobRunListResponse(
        items=[DefiJobRunSummary.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@defi_observability_admin_router.get("/jobs/{run_id}", response_model=DefiJobRunSummary)
def get_defi_observability_job(
    run_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    row = get_job_run_admin(db, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job_run_not_found")
    return DefiJobRunSummary.model_validate(row)
