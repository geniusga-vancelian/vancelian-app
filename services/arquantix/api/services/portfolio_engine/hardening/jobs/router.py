"""Admin endpoints for rebuild/replay jobs (Hardening Subphase 2)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from ..security.context import ActorContext
from ..security.dependencies import require_admin_or_ops
from .repository import JobRunRepository
from .schemas import JobRunListResponse, JobRunRead, RebuildResult
from .service import PortfolioNotFoundForRebuildError, RebuildService

router = APIRouter()
_service = RebuildService()
_repo = JobRunRepository()
_guard = require_admin_or_ops()


# ------------------------------------------------------------------
# Rebuild endpoints
# ------------------------------------------------------------------

@router.post(
    "/portfolios/{portfolio_id}/rebuild-positions",
    response_model=RebuildResult,
    status_code=200,
)
def rebuild_positions(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _service.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio_id,
        )
        db.commit()
        return result
    except PortfolioNotFoundForRebuildError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.post(
    "/portfolios/{portfolio_id}/rebuild-valuations",
    response_model=RebuildResult,
    status_code=200,
)
def rebuild_valuations(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _service.run_rebuild_job(
            db, job_type="rebuild_valuations", portfolio_id=portfolio_id,
        )
        db.commit()
        return result
    except PortfolioNotFoundForRebuildError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.post(
    "/portfolios/{portfolio_id}/rebuild-performance",
    response_model=RebuildResult,
    status_code=200,
)
def rebuild_performance(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _service.run_rebuild_job(
            db, job_type="rebuild_performance", portfolio_id=portfolio_id,
        )
        db.commit()
        return result
    except PortfolioNotFoundForRebuildError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


# ------------------------------------------------------------------
# Job run endpoints
# ------------------------------------------------------------------

@router.get("/jobs", response_model=JobRunListResponse)
def list_jobs(
    job_type: Optional[str] = Query(None),
    scope_type: Optional[str] = Query(None),
    scope_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _repo.list_runs(
        db,
        job_type=job_type,
        scope_type=scope_type,
        scope_id=scope_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return JobRunListResponse(
        items=[JobRunRead.model_validate(r) for r in items],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=JobRunRead)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    run = _repo.get_by_id(db, job_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JobRun {job_id} not found",
        )
    return JobRunRead.model_validate(run)
