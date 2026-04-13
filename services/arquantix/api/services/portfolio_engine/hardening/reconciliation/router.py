"""Admin endpoints for reconciliation (Hardening Subphase 3)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from ..security.context import ActorContext
from ..security.dependencies import require_admin_or_ops
from .repository import ReconciliationReportRepository
from .schemas import (
    ReconciliationReportListResponse,
    ReconciliationReportRead,
    ReconciliationResult,
)
from .service import PortfolioNotFoundForReconciliationError, ReconciliationService

router = APIRouter()
_service = ReconciliationService()
_repo = ReconciliationReportRepository()
_guard = require_admin_or_ops()


# ------------------------------------------------------------------
# Portfolio-level reconciliation
# ------------------------------------------------------------------

@router.post(
    "/portfolios/{portfolio_id}/reconcile-trades-positions",
    response_model=ReconciliationResult,
)
def reconcile_trades_positions(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _service.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio_id,
        )
        db.commit()
        return result
    except PortfolioNotFoundForReconciliationError:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")


@router.post(
    "/portfolios/{portfolio_id}/reconcile-positions-valuations",
    response_model=ReconciliationResult,
)
def reconcile_positions_valuations(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _service.run_reconciliation_job(
            db, reconciliation_type="positions_vs_valuations", portfolio_id=portfolio_id,
        )
        db.commit()
        return result
    except PortfolioNotFoundForReconciliationError:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")


@router.post(
    "/portfolios/{portfolio_id}/reconcile-valuations-performance",
    response_model=ReconciliationResult,
)
def reconcile_valuations_performance(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _service.run_reconciliation_job(
            db, reconciliation_type="valuations_vs_performance", portfolio_id=portfolio_id,
        )
        db.commit()
        return result
    except PortfolioNotFoundForReconciliationError:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")


# ------------------------------------------------------------------
# Global reconciliation
# ------------------------------------------------------------------

@router.post(
    "/ledger/reconcile-balances",
    response_model=ReconciliationResult,
)
def reconcile_ledger_balances(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    result = _service.run_reconciliation_job(
        db, reconciliation_type="ledger_entries_vs_balances",
    )
    db.commit()
    return result


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------

@router.get(
    "/reconciliation-reports",
    response_model=ReconciliationReportListResponse,
)
def list_reconciliation_reports(
    reconciliation_type: Optional[str] = Query(None),
    scope_type: Optional[str] = Query(None),
    scope_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _repo.list_reports(
        db,
        reconciliation_type=reconciliation_type,
        scope_type=scope_type,
        scope_id=scope_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return ReconciliationReportListResponse(
        items=[ReconciliationReportRead.model_validate(r) for r in items],
        total=total,
    )


@router.get(
    "/reconciliation-reports/{report_id}",
    response_model=ReconciliationReportRead,
)
def get_reconciliation_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    report = _repo.get_by_id(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"ReconciliationReport {report_id} not found")
    return ReconciliationReportRead.model_validate(report)
