"""API routes for Pool Interest Engine (Phase 2A.7)."""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from .interest_engine import InterestEngine, InterestEngineError
from .pool_models import LendingPool

router = APIRouter(prefix="/api/lending/interest", tags=["Pool Interest Engine"])
_engine = InterestEngine()


# ── Schemas ───────────────────────────────────────────────────────

class RunAccrualRequest(BaseModel):
    accrual_date: Optional[date] = None


class UpdatePoolRatesRequest(BaseModel):
    borrow_rate_bps: Decimal = Field(..., ge=0, le=10000)
    supply_rate_bps: Decimal = Field(..., ge=0, le=10000)


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/run-accrual")
def run_daily_accrual(payload: RunAccrualRequest = RunAccrualRequest(), db: Session = Depends(get_db)):
    """Run daily interest accrual for all active pools.

    Idempotent: if already run for the given date, pools are skipped.
    """
    try:
        result = _engine.run_daily_accrual(db, accrual_date=payload.accrual_date)
        db.commit()
        return result
    except InterestEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/snapshots/{asset}")
def get_pool_snapshots(
    asset: str,
    limit: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get daily interest snapshots for a pool."""
    pool = db.query(LendingPool).filter(
        LendingPool.asset == asset.upper(), LendingPool.status == "active",
    ).first()
    if not pool:
        return {"asset": asset.upper(), "snapshots": []}

    snapshots = _engine.get_snapshots(db, pool.id, limit=limit)
    return {
        "asset": pool.asset,
        "pool_id": str(pool.id),
        "borrow_rate_bps": float(pool.borrow_rate_bps),
        "supply_rate_bps": float(pool.supply_rate_bps),
        "snapshots": [
            {
                "date": s.date.isoformat(),
                "total_borrowed": float(s.total_borrowed),
                "interest_generated": float(s.interest_generated),
                "interest_to_lenders": float(s.interest_to_lenders),
                "platform_fee": float(s.platform_fee),
            }
            for s in snapshots
        ],
    }


@router.get("/accrued")
def get_accrued_interest(
    client_id: UUID = Query(...),
    asset: str = Query(...),
    role: str = Query("lender", pattern="^(lender|borrower)$"),
    db: Session = Depends(get_db),
):
    """Get total accrued interest for a client in a pool."""
    pool = db.query(LendingPool).filter(
        LendingPool.asset == asset.upper(), LendingPool.status == "active",
    ).first()
    if not pool:
        return {"client_id": str(client_id), "asset": asset.upper(), "total_accrued": 0.0}

    total = _engine.get_total_accrued_interest(db, client_id, pool.id, role=role)
    return {
        "client_id": str(client_id),
        "asset": pool.asset,
        "role": role,
        "total_accrued": float(total),
    }


@router.put("/rates/{asset}")
def update_pool_rates(
    asset: str,
    payload: UpdatePoolRatesRequest,
    db: Session = Depends(get_db),
):
    """Update borrow/supply APR rates for a pool (in basis points)."""
    pool = db.query(LendingPool).filter(
        LendingPool.asset == asset.upper(), LendingPool.status == "active",
    ).first()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No active pool for {asset}")

    if payload.supply_rate_bps > payload.borrow_rate_bps:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="supply_rate_bps cannot exceed borrow_rate_bps",
        )

    pool.borrow_rate_bps = payload.borrow_rate_bps
    pool.supply_rate_bps = payload.supply_rate_bps
    db.commit()

    return {
        "asset": pool.asset,
        "borrow_rate_bps": float(pool.borrow_rate_bps),
        "supply_rate_bps": float(pool.supply_rate_bps),
        "spread_bps": float(payload.borrow_rate_bps - payload.supply_rate_bps),
    }
