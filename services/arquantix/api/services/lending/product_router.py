"""Earn / Borrow Product Surface API — Phase 2A.9.

Flutter-ready endpoints for the Earn/Borrow product screens.
Read-only aggregation layer on top of the pool lending engine.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .product_surface import (
    get_pools_overview,
    get_earn_positions,
    get_borrow_positions,
    get_earn_borrow_dashboard,
)

router = APIRouter(prefix="/api/lending", tags=["Earn / Borrow Product"])


@router.get("/pools")
def list_pools(db: Session = Depends(get_db)):
    """All active lending pools with rates, liquidity and utilization.

    Used for the pool list / market overview screen.
    """
    return {"pools": get_pools_overview(db)}


@router.get("/earn/positions")
def earn_positions(
    client_id: UUID = Query(..., description="Client UUID"),
    db: Session = Depends(get_db),
):
    """Lender-facing: supplied amounts, accrued interest, APY per asset.

    Used for the "Earn" screen.
    """
    try:
        return get_earn_positions(db, client_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing earn positions: {exc}",
        )


@router.get("/borrow/positions")
def borrow_positions(
    client_id: UUID = Query(..., description="Client UUID"),
    db: Session = Depends(get_db),
):
    """Borrower-facing: borrowed amounts, accrued interest, total due per position.

    Used for the "Borrow" screen.
    """
    try:
        return get_borrow_positions(db, client_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing borrow positions: {exc}",
        )


@router.get("/dashboard")
def earn_borrow_dashboard(
    client_id: UUID = Query(..., description="Client UUID"),
    db: Session = Depends(get_db),
):
    """Combined Earn + Borrow dashboard — single call for the main screen.

    Returns summary of earn value, borrow liability, and net position.
    """
    try:
        return get_earn_borrow_dashboard(db, client_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing dashboard: {exc}",
        )
