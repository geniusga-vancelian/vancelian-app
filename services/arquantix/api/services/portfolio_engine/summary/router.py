"""Read-only router for portfolio summary (Portfolio Engine)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from ..hardening.authorization.dependencies import require_portfolio_access
from .schemas import PortfolioSummaryResponse
from .service import PortfolioNotFoundForSummaryError, PortfolioSummaryService

router = APIRouter()

_service = PortfolioSummaryService()


@router.get(
    "/portfolios/{portfolio_id}/summary",
    response_model=PortfolioSummaryResponse,
)
def get_portfolio_summary(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        return _service.get_summary(db, portfolio_id)
    except PortfolioNotFoundForSummaryError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
