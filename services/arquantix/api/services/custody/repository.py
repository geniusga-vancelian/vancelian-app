"""Repository layer for custody tables."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from .models import (
    CustodyProvider,
    CustodyAccount,
    CustodyAccountBalance,
    CustodyTransaction,
    CustodyWebhookEvent,
)


class OptimisticLockError(Exception):
    """Raised when a balance update fails due to version mismatch."""

    def __init__(self, account_id: UUID, expected: int, actual: int):
        super().__init__(
            f"Optimistic lock failed for account {account_id}: "
            f"expected version {expected}, got {actual}"
        )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class CustodyProviderRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> CustodyProvider:
        provider = CustodyProvider(**data)
        db.add(provider)
        db.flush()
        return provider

    @staticmethod
    def get_by_id(db: Session, provider_id: UUID) -> CustodyProvider | None:
        return db.query(CustodyProvider).filter(CustodyProvider.id == provider_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> CustodyProvider | None:
        return db.query(CustodyProvider).filter(CustodyProvider.name == name).first()

    @staticmethod
    def list(db: Session, *, skip: int = 0, limit: int = 50) -> tuple[list[CustodyProvider], int]:
        query = db.query(CustodyProvider)
        total = query.count()
        items = query.order_by(CustodyProvider.created_at.desc()).offset(skip).limit(limit).all()
        return items, total


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class CustodyAccountRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> CustodyAccount:
        account = CustodyAccount(**data)
        db.add(account)
        db.flush()
        return account

    @staticmethod
    def get_by_id(db: Session, account_id: UUID) -> CustodyAccount | None:
        return db.query(CustodyAccount).filter(CustodyAccount.id == account_id).first()

    @staticmethod
    def find_by_iban(db: Session, iban: str) -> CustodyAccount | None:
        return (
            db.query(CustodyAccount)
            .filter(CustodyAccount.iban == iban, CustodyAccount.status == "active")
            .first()
        )

    @staticmethod
    def find_client_account(db: Session, client_id: UUID, currency: str) -> CustodyAccount | None:
        return (
            db.query(CustodyAccount)
            .filter(
                CustodyAccount.client_id == client_id,
                CustodyAccount.currency == currency,
                CustodyAccount.account_type == "client_deposit_account",
                CustodyAccount.status == "active",
            )
            .first()
        )

    @staticmethod
    def find_settlement_account(db: Session, currency: str) -> CustodyAccount | None:
        return (
            db.query(CustodyAccount)
            .filter(
                CustodyAccount.account_type == "company_settlement_account",
                CustodyAccount.is_master_account.is_(True),
                CustodyAccount.currency == currency,
                CustodyAccount.status == "active",
            )
            .first()
        )

    @staticmethod
    def list(
        db: Session,
        *,
        account_type: str | None = None,
        client_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CustodyAccount], int]:
        query = db.query(CustodyAccount)
        if account_type:
            query = query.filter(CustodyAccount.account_type == account_type)
        if client_id:
            query = query.filter(CustodyAccount.client_id == client_id)
        total = query.count()
        items = query.order_by(CustodyAccount.created_at.desc()).offset(skip).limit(limit).all()
        return items, total


# ---------------------------------------------------------------------------
# Balances (with optimistic locking + SELECT FOR UPDATE)
# ---------------------------------------------------------------------------

class CustodyBalanceRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> CustodyAccountBalance:
        balance = CustodyAccountBalance(**data)
        db.add(balance)
        db.flush()
        return balance

    @staticmethod
    def get_by_account_id(db: Session, account_id: UUID) -> CustodyAccountBalance | None:
        return (
            db.query(CustodyAccountBalance)
            .filter(CustodyAccountBalance.account_id == account_id)
            .first()
        )

    @staticmethod
    def get_for_update(db: Session, account_id: UUID) -> CustodyAccountBalance | None:
        """Acquire a row-level lock (SELECT … FOR UPDATE) to prevent concurrent modifications."""
        return (
            db.query(CustodyAccountBalance)
            .filter(CustodyAccountBalance.account_id == account_id)
            .with_for_update()
            .first()
        )

    @staticmethod
    def update_balance(
        db: Session,
        balance: CustodyAccountBalance,
        *,
        delta: Decimal,
        expected_version: int | None = None,
    ) -> CustodyAccountBalance:
        if expected_version is not None and balance.version != expected_version:
            raise OptimisticLockError(balance.account_id, expected_version, balance.version)
        balance.available_balance = Decimal(str(balance.available_balance)) + delta
        balance.version += 1
        balance.last_updated_at = func.now()
        db.flush()
        return balance

    @staticmethod
    def list(db: Session, *, skip: int = 0, limit: int = 50) -> tuple[list[CustodyAccountBalance], int]:
        query = db.query(CustodyAccountBalance)
        total = query.count()
        items = query.order_by(CustodyAccountBalance.last_updated_at.desc()).offset(skip).limit(limit).all()
        return items, total


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class CustodyTransactionRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> CustodyTransaction:
        tx = CustodyTransaction(**data)
        db.add(tx)
        db.flush()
        return tx

    @staticmethod
    def get_by_id(db: Session, tx_id: UUID) -> CustodyTransaction | None:
        return db.query(CustodyTransaction).filter(CustodyTransaction.id == tx_id).first()

    @staticmethod
    def find_by_provider_and_ref(
        db: Session, provider_id: UUID, external_reference: str
    ) -> CustodyTransaction | None:
        return (
            db.query(CustodyTransaction)
            .filter(
                CustodyTransaction.provider_id == provider_id,
                CustodyTransaction.external_reference == external_reference,
            )
            .first()
        )

    @staticmethod
    def find_by_external_reference(
        db: Session, external_reference: str
    ) -> CustodyTransaction | None:
        return (
            db.query(CustodyTransaction)
            .filter(CustodyTransaction.external_reference == external_reference)
            .first()
        )

    @staticmethod
    def update_status(
        db: Session,
        tx: CustodyTransaction,
        *,
        new_status: str,
        failure_reason: str | None = None,
    ) -> CustodyTransaction:
        tx.status = new_status
        if failure_reason is not None:
            tx.failure_reason = failure_reason
        db.flush()
        return tx

    @staticmethod
    def list(
        db: Session,
        *,
        account_id: Optional[UUID] = None,
        client_id: Optional[UUID] = None,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        provider_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CustodyTransaction], int]:
        query = db.query(CustodyTransaction)
        if account_id:
            query = query.filter(CustodyTransaction.account_id == account_id)
        if client_id:
            query = query.join(
                CustodyAccount, CustodyTransaction.account_id == CustodyAccount.id
            ).filter(CustodyAccount.client_id == client_id)
        if transaction_type:
            query = query.filter(CustodyTransaction.transaction_type == transaction_type)
        if status:
            query = query.filter(CustodyTransaction.status == status)
        if provider_id:
            query = query.filter(CustodyTransaction.provider_id == provider_id)
        total = query.count()
        items = query.order_by(CustodyTransaction.created_at.desc()).offset(skip).limit(limit).all()
        return items, total


# ---------------------------------------------------------------------------
# Webhook Events
# ---------------------------------------------------------------------------

class CustodyWebhookEventRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> CustodyWebhookEvent:
        event = CustodyWebhookEvent(**data)
        db.add(event)
        db.flush()
        return event

    @staticmethod
    def get_by_id(db: Session, event_id: UUID) -> CustodyWebhookEvent | None:
        return db.query(CustodyWebhookEvent).filter(CustodyWebhookEvent.id == event_id).first()

    @staticmethod
    def find_by_provider_and_ref(
        db: Session, provider_id: UUID, external_reference: str
    ) -> CustodyWebhookEvent | None:
        """Find the most recent event for a given (provider, external_reference) pair."""
        return (
            db.query(CustodyWebhookEvent)
            .filter(
                CustodyWebhookEvent.provider_id == provider_id,
                CustodyWebhookEvent.external_reference == external_reference,
            )
            .order_by(CustodyWebhookEvent.received_at.desc())
            .first()
        )

    @staticmethod
    def update_status(
        db: Session,
        event: CustodyWebhookEvent,
        *,
        status: str,
        error_message: str | None = None,
        linked_transaction_id: UUID | None = None,
    ) -> CustodyWebhookEvent:
        event.processing_status = status
        if error_message is not None:
            event.error_message = error_message
        if linked_transaction_id is not None:
            event.linked_transaction_id = linked_transaction_id
        event.processed_at = func.now()
        db.flush()
        return event

    @staticmethod
    def list(
        db: Session,
        *,
        provider_id: UUID | None = None,
        processing_status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CustodyWebhookEvent], int]:
        query = db.query(CustodyWebhookEvent)
        if provider_id:
            query = query.filter(CustodyWebhookEvent.provider_id == provider_id)
        if processing_status:
            query = query.filter(CustodyWebhookEvent.processing_status == processing_status)
        total = query.count()
        items = query.order_by(CustodyWebhookEvent.received_at.desc()).offset(skip).limit(limit).all()
        return items, total
