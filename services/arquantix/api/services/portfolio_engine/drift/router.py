"""FastAPI router for Drift Detection & Rebalance Engine (Phase 6).

Endpoints are resource-nested under /portfolios/, mounted without prefix.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from ..rebalance_preview.schemas import PreviewRead
from .schemas import DriftReport, RebalancePreviewResponse
from .service import DriftRebalanceService, PortfolioNotFoundForDriftError
from ..hardening.authorization.dependencies import require_portfolio_access

router = APIRouter()
_service = DriftRebalanceService()


@router.get(
    "/portfolios/{portfolio_id}/drift",
    response_model=DriftReport,
)
def get_portfolio_drift(
    portfolio_id: UUID,
    threshold: Optional[Decimal] = Query(None, ge=0, le=1),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        return _service.detect_drift(db, portfolio_id, threshold=threshold)
    except PortfolioNotFoundForDriftError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/portfolios/{portfolio_id}/rebalance-preview",
    response_model=RebalancePreviewResponse,
)
def get_rebalance_preview(
    portfolio_id: UUID,
    threshold: Optional[Decimal] = Query(None, ge=0, le=1),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        return _service.generate_rebalance_preview(
            db, portfolio_id, threshold=threshold,
        )
    except PortfolioNotFoundForDriftError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.post(
    "/portfolios/{portfolio_id}/rebalance-plan",
    response_model=PreviewRead,
    status_code=201,
)
def create_rebalance_plan(
    portfolio_id: UUID,
    threshold: Optional[Decimal] = Query(None, ge=0, le=1),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        preview = _service.create_rebalance_plan(
            db, portfolio_id, threshold=threshold,
        )
        db.commit()
        db.refresh(preview)
        return PreviewRead.model_validate(preview)
    except PortfolioNotFoundForDriftError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
