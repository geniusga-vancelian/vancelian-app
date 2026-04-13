"""Wallet Containers API endpoints (Portfolio Engine — ledger layer)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import WalletCreate, WalletListResponse, WalletRead, WalletUpdate
from .service import (
    InstrumentReferenceError,
    PortfolioReferenceError,
    WalletContainerService,
    WalletNotFoundError,
)

router = APIRouter()

_service = WalletContainerService()


@router.get("", response_model=WalletListResponse)
def list_wallets(
    client_id: Optional[UUID] = Query(None, description="Filter by client_id"),
    portfolio_id: Optional[UUID] = Query(None, description="Filter by portfolio_id"),
    wallet_type: Optional[str] = Query(None, description="Filter by wallet_type"),
    wallet_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_wallets(
        db, client_id=client_id, portfolio_id=portfolio_id,
        wallet_type=wallet_type, status=wallet_status, skip=skip, limit=limit,
    )
    return WalletListResponse(
        items=[WalletRead.model_validate(w) for w in items],
        total=total,
    )


@router.post("", response_model=WalletRead, status_code=status.HTTP_201_CREATED)
def create_wallet(
    payload: WalletCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        wallet = _service.create_wallet(db, payload)
        db.commit()
        db.refresh(wallet)
        return WalletRead.model_validate(wallet)
    except PortfolioReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except InstrumentReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{wallet_id}", response_model=WalletRead)
def get_wallet(
    wallet_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        wallet = _service.get_wallet(db, wallet_id)
        return WalletRead.model_validate(wallet)
    except WalletNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WalletContainer not found")


@router.patch("/{wallet_id}", response_model=WalletRead)
def update_wallet(
    wallet_id: UUID,
    payload: WalletUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        wallet = _service.update_wallet(db, wallet_id, payload)
        db.commit()
        db.refresh(wallet)
        return WalletRead.model_validate(wallet)
    except WalletNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WalletContainer not found")
    except PortfolioReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except InstrumentReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
