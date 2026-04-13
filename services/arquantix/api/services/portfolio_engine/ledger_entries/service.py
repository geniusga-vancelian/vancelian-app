"""Service layer for Ledger Entries module (Portfolio Engine — accounting layer).

Core financial primitive: double-entry posting.
Entries are NEVER updated or deleted.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..ledger_accounts.models import LedgerAccount
from .models import LedgerEntry
from .repository import LedgerEntryRepository


class LedgerEntryNotFoundError(Exception):
    def __init__(self, entry_id: UUID):
        self.entry_id = entry_id
        super().__init__(f"LedgerEntry {entry_id} not found")


class AccountNotFoundError(Exception):
    def __init__(self, account_id: UUID):
        self.account_id = account_id
        super().__init__(f"LedgerAccount {account_id} not found")


class CurrencyMismatchError(Exception):
    def __init__(self, account_id: UUID, expected: str, got: str):
        super().__init__(
            f"Currency mismatch for account {account_id}: expected {expected}, got {got}"
        )


class InactiveAccountError(Exception):
    def __init__(self, account_id: UUID):
        self.account_id = account_id
        super().__init__(f"LedgerAccount {account_id} is not active")


class AssetMismatchError(Exception):
    def __init__(self, account_id: UUID, expected: UUID, got: UUID):
        super().__init__(
            f"Asset mismatch for account {account_id}: account has {expected}, got {got}"
        )


class LedgerEntryService:

    def __init__(self) -> None:
        self._repo = LedgerEntryRepository()

    @staticmethod
    def _load_account(db: Session, account_id: UUID) -> LedgerAccount:
        account = db.query(LedgerAccount).filter(LedgerAccount.id == account_id).first()
        if account is None:
            raise AccountNotFoundError(account_id)
        if account.status != "active":
            raise InactiveAccountError(account_id)
        return account

    @staticmethod
    def _resolve_asset_id(
        asset_id: Optional[UUID],
        debit_account: "LedgerAccount",
        credit_account: "LedgerAccount",
    ) -> Optional[UUID]:
        """Resolve asset_id: use explicit value, fallback to account asset_id, or None."""
        if asset_id is not None:
            if debit_account.asset_id is not None and debit_account.asset_id != asset_id:
                raise AssetMismatchError(debit_account.id, debit_account.asset_id, asset_id)
            if credit_account.asset_id is not None and credit_account.asset_id != asset_id:
                raise AssetMismatchError(credit_account.id, credit_account.asset_id, asset_id)
            return asset_id
        return debit_account.asset_id

    def post_double_entry(
        self,
        db: Session,
        *,
        debit_account_id: UUID,
        credit_account_id: UUID,
        amount: Decimal,
        currency: str,
        reference_type: str,
        reference_id: Optional[UUID] = None,
        effective_at: datetime,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
        asset_id: Optional[UUID] = None,
    ) -> tuple[LedgerEntry, LedgerEntry]:
        """Create exactly 2 ledger entries (debit + credit) and update account balances atomically.

        Args:
            asset_id: If provided, written to both entries and validated against account
                asset_ids. If omitted, resolved from debit_account.asset_id (may be None
                for legacy accounts without asset_id).
        """
        if amount <= 0:
            raise ValueError("Ledger entry amount must be positive")

        debit_account = self._load_account(db, debit_account_id)
        credit_account = self._load_account(db, credit_account_id)

        if debit_account.currency != currency:
            raise CurrencyMismatchError(debit_account_id, debit_account.currency, currency)
        if credit_account.currency != currency:
            raise CurrencyMismatchError(credit_account_id, credit_account.currency, currency)

        resolved_asset_id = self._resolve_asset_id(asset_id, debit_account, credit_account)
        meta = metadata or {}

        entry_data_base = {
            "amount": amount,
            "currency": currency,
            "asset_id": resolved_asset_id,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "description": description,
            "effective_at": effective_at,
            "metadata_": meta,
        }

        debit_entry = self._repo.create(db, data={
            "account_id": debit_account_id,
            "entry_type": "debit",
            **entry_data_base,
        })

        credit_entry = self._repo.create(db, data={
            "account_id": credit_account_id,
            "entry_type": "credit",
            **entry_data_base,
        })

        debit_entry.counterpart_entry_id = credit_entry.id
        credit_entry.counterpart_entry_id = debit_entry.id

        debit_account.balance = Decimal(str(debit_account.balance)) + amount
        credit_account.balance = Decimal(str(credit_account.balance)) - amount

        db.flush()
        return debit_entry, credit_entry

    def get_entry(self, db: Session, entry_id: UUID) -> LedgerEntry:
        entry = self._repo.get_by_id(db, entry_id)
        if entry is None:
            raise LedgerEntryNotFoundError(entry_id)
        return entry

    def list_entries(
        self,
        db: Session,
        *,
        account_id: Optional[UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LedgerEntry], int]:
        return self._repo.list(
            db, account_id=account_id, reference_type=reference_type,
            reference_id=reference_id, skip=skip, limit=limit,
        )
