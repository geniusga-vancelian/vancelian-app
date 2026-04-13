"""Ledger Entries API endpoints (Portfolio Engine — accounting layer).

Read-only: entries are created only through internal service methods, never via API POST.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops
from .schemas import LedgerEntryListResponse, LedgerEntryRead
from .service import LedgerEntryNotFoundError, LedgerEntryService

router = APIRouter()

_service = LedgerEntryService()
_guard = require_admin_or_ops()


@router.get("", response_model=LedgerEntryListResponse)
def list_ledger_entries(
    account_id: Optional[UUID] = Query(None, description="Filter by account_id"),
    reference_type: Optional[str] = Query(None, description="Filter by reference_type"),
    reference_id: Optional[UUID] = Query(None, description="Filter by reference_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _service.list_entries(
        db, account_id=account_id, reference_type=reference_type,
        reference_id=reference_id, skip=skip, limit=limit,
    )
    return LedgerEntryListResponse(
        items=[LedgerEntryRead.model_validate(e) for e in items],
        total=total,
    )


@router.get("/{entry_id}", response_model=LedgerEntryRead)
def get_ledger_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        entry = _service.get_entry(db, entry_id)
        return LedgerEntryRead.model_validate(entry)
    except LedgerEntryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LedgerEntry not found")
