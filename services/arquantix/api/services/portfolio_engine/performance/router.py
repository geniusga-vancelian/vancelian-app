"""FastAPI router for the Performance & Benchmark Engine (Phase 9)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import (
    BenchmarkComparison,
    PerformanceSeriesResponse,
    PerformanceSummary,
)
from .service import PerformanceService, PortfolioNotFoundForPerformanceError
from ..hardening.authorization.dependencies import require_portfolio_access

router = APIRouter()
_service = PerformanceService()


@router.get(
    "/portfolios/{portfolio_id}/performance",
    response_model=PerformanceSummary,
)
def get_portfolio_performance(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        return _service.compute_portfolio_performance(db, portfolio_id)
    except PortfolioNotFoundForPerformanceError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/portfolios/{portfolio_id}/performance-series",
    response_model=PerformanceSeriesResponse,
)
def get_performance_series(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        return _service.compute_performance_series(db, portfolio_id)
    except PortfolioNotFoundForPerformanceError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/portfolios/{portfolio_id}/benchmark",
    response_model=BenchmarkComparison,
)
def get_benchmark_comparison(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        return _service.compare_to_benchmark(db, portfolio_id)
    except PortfolioNotFoundForPerformanceError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
