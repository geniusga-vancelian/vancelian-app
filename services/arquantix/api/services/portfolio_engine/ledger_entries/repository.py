"""Repository layer for pe_ledger_entries (Portfolio Engine — accounting layer).

INSERT-ONLY: no update or delete methods are provided.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import LedgerEntry


class LedgerEntryRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> LedgerEntry:
        entry = LedgerEntry(**data)
        db.add(entry)
        db.flush()
        return entry

    @staticmethod
    def get_by_id(db: Session, entry_id: UUID) -> Optional[LedgerEntry]:
        return db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        account_id: Optional[UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LedgerEntry], int]:
        query = db.query(LedgerEntry)
        if account_id:
            query = query.filter(LedgerEntry.account_id == account_id)
        if reference_type:
            query = query.filter(LedgerEntry.reference_type == reference_type)
        if reference_id:
            query = query.filter(LedgerEntry.reference_id == reference_id)
        total = query.count()
        items = query.order_by(LedgerEntry.effective_at.desc()).offset(skip).limit(limit).all()
        return items, total
