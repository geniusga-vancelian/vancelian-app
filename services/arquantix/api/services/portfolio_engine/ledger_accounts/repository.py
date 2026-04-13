"""Repository layer for pe_ledger_accounts (Portfolio Engine — accounting layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import LedgerAccount


class LedgerAccountRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> LedgerAccount:
        account = LedgerAccount(**data)
        db.add(account)
        db.flush()
        return account

    @staticmethod
    def get_by_id(db: Session, account_id: UUID) -> Optional[LedgerAccount]:
        return db.query(LedgerAccount).filter(LedgerAccount.id == account_id).first()

    @staticmethod
    def get_by_code(db: Session, account_code: str) -> Optional[LedgerAccount]:
        return db.query(LedgerAccount).filter(LedgerAccount.account_code == account_code).first()

    @staticmethod
    def list(
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        account_type: Optional[str] = None,
        currency: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LedgerAccount], int]:
        query = db.query(LedgerAccount)
        if client_id:
            query = query.filter(LedgerAccount.client_id == client_id)
        if account_type:
            query = query.filter(LedgerAccount.account_type == account_type)
        if currency:
            query = query.filter(LedgerAccount.currency == currency)
        if status:
            query = query.filter(LedgerAccount.status == status)
        total = query.count()
        items = query.order_by(LedgerAccount.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, account: LedgerAccount, *, data: dict) -> LedgerAccount:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(account, col_name, value)
        db.flush()
        return account
