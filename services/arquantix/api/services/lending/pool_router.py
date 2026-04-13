"""API routes for Pool-based P2P Lending (Phase 2A.6bis + 2A.8)."""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from .pool_service import (
    PoolLendingService,
    PoolError,
    InsufficientBalanceError,
    InsufficientPoolLiquidityError,
    CommitmentNotFoundError,
)
from .repayment_engine import (
    RepaymentEngine,
    RepaymentError,
    BorrowPositionNotFoundError,
)
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError

router = APIRouter(prefix="/api/lending/pool", tags=["Pool Lending"])
_svc = PoolLendingService()
_repay = RepaymentEngine()


# ── Schemas ───────────────────────────────────────────────────────

class SupplyRequest(BaseModel):
    client_id: UUID
    asset: str = Field(..., min_length=1, max_length=20)
    amount: Decimal = Field(..., gt=0)


class BorrowRequest(BaseModel):
    client_id: UUID
    asset: str = Field(..., min_length=1, max_length=20)
    amount: Decimal = Field(..., gt=0)


class CancelCommitmentRequest(BaseModel):
    client_id: UUID


class RepayRequest(BaseModel):
    borrow_position_id: UUID


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/supply", status_code=status.HTTP_201_CREATED)
def create_supply(payload: SupplyRequest, db: Session = Depends(get_db)):
    """Lender commits liquidity to the pool.

    Funds stay in spot but available_balance is reduced (reserved).
    """
    try:
        commitment = _svc.create_supply_commitment(
            db,
            client_id=payload.client_id,
            asset=payload.asset,
            amount=payload.amount,
        )
        db.commit()
        return {
            "commitment_id": str(commitment.id),
            "pool_id": str(commitment.pool_id),
            "asset": commitment.asset,
            "amount": float(commitment.amount),
            "status": commitment.status,
        }
    except ClientNotEligibleError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except InsufficientBalanceError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except PoolError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/borrow")
def borrow_from_pool(payload: BorrowRequest, db: Session = Depends(get_db)):
    """Borrow from the pool — atomic FIFO allocation."""
    try:
        result = _svc.borrow_from_pool(
            db,
            borrower_client_id=payload.client_id,
            asset=payload.asset,
            amount=payload.amount,
        )
        db.commit()
        return result
    except ClientNotEligibleError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except InsufficientPoolLiquidityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except PoolError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/repay")
def repay_borrow(payload: RepayRequest, db: Session = Depends(get_db)):
    """Full repayment of a borrow position.

    Settles principal + accrued interest, credits lenders, closes positions.
    """
    try:
        result = _repay.repay_borrow_position(
            db, borrow_position_id=payload.borrow_position_id,
        )
        db.commit()
        return result
    except BorrowPositionNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientBalanceError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RepaymentError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except PoolError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/supply/{commitment_id}")
def cancel_commitment(
    commitment_id: UUID,
    payload: CancelCommitmentRequest,
    db: Session = Depends(get_db),
):
    """Cancel an unused supply commitment."""
    try:
        commitment = _svc.cancel_supply_commitment(db, commitment_id, payload.client_id)
        db.commit()
        return {
            "commitment_id": str(commitment.id),
            "status": commitment.status,
        }
    except CommitmentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PoolError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/status/{asset}")
def get_pool_status(asset: str, db: Session = Depends(get_db)):
    """Get pool status, liquidity and utilization for an asset."""
    return _svc.get_pool_summary(db, asset)


@router.get("/commitments")
def list_commitments(
    client_id: Optional[UUID] = Query(None),
    asset: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List supply commitments, optionally by client or asset."""
    pool_id = None
    if asset:
        pool = _svc.get_pool(db, asset)
        pool_id = pool.id if pool else None
    commitments = _svc.list_commitments(db, client_id=client_id, pool_id=pool_id)
    return [
        {
            "id": str(c.id),
            "pool_id": str(c.pool_id),
            "client_id": str(c.client_id),
            "asset": c.asset,
            "amount": float(c.amount),
            "available_amount": float(c.available_amount),
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in commitments
    ]


@router.get("/borrows")
def list_borrows(
    client_id: Optional[UUID] = Query(None),
    asset: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List borrow positions, optionally by client or asset."""
    pool_id = None
    if asset:
        pool = _svc.get_pool(db, asset)
        pool_id = pool.id if pool else None
    borrows = _svc.list_borrow_positions(db, client_id=client_id, pool_id=pool_id)
    return [
        {
            "id": str(b.id),
            "pool_id": str(b.pool_id),
            "client_id": str(b.client_id),
            "asset": b.asset,
            "borrowed_amount": float(b.borrowed_amount),
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in borrows
    ]
