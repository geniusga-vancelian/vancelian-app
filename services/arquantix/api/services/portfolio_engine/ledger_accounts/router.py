"""Ledger Accounts API endpoints (Portfolio Engine — accounting layer)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops
from .schemas import LedgerAccountCreate, LedgerAccountListResponse, LedgerAccountRead, LedgerAccountUpdate
from .service import (
    AssetReferenceError,
    ClientReferenceError,
    DuplicateAccountCodeError,
    LedgerAccountNotFoundError,
    LedgerAccountService,
    WalletContainerReferenceError,
)

router = APIRouter()

_service = LedgerAccountService()
_guard = require_admin_or_ops()


@router.get("", response_model=LedgerAccountListResponse)
def list_ledger_accounts(
    client_id: Optional[UUID] = Query(None, description="Filter by client_id"),
    account_type: Optional[str] = Query(None, description="Filter by account_type"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    account_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _service.list_accounts(
        db, client_id=client_id, account_type=account_type,
        currency=currency, status=account_status, skip=skip, limit=limit,
    )
    return LedgerAccountListResponse(
        items=[LedgerAccountRead.model_validate(a) for a in items],
        total=total,
    )


@router.post("", response_model=LedgerAccountRead, status_code=status.HTTP_201_CREATED)
def create_ledger_account(
    payload: LedgerAccountCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        account = _service.create_account(db, payload)
        db.commit()
        db.refresh(account)
        return LedgerAccountRead.model_validate(account)
    except DuplicateAccountCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ClientReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except AssetReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except WalletContainerReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{account_id}", response_model=LedgerAccountRead)
def get_ledger_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        account = _service.get_account(db, account_id)
        return LedgerAccountRead.model_validate(account)
    except LedgerAccountNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LedgerAccount not found")


@router.patch("/{account_id}", response_model=LedgerAccountRead)
def update_ledger_account(
    account_id: UUID,
    payload: LedgerAccountUpdate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        account = _service.update_account(db, account_id, payload)
        db.commit()
        db.refresh(account)
        return LedgerAccountRead.model_validate(account)
    except LedgerAccountNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LedgerAccount not found")
    except WalletContainerReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
