"""Repository for crypto custody accounts and balances."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .custody_models import CryptoCustodyAccount, CryptoCustodyBalance

DEFAULT_PROVIDER = "fireblocks"
ACCOUNT_TYPE_CLIENTS_POOL = "clients_pool"
ACCOUNT_TYPE_SETTLEMENT_WALLET = "settlement_wallet"


class CryptoCustodyAccountRepository:
    @staticmethod
    def get_by_asset_and_type(
        db: Session,
        asset: str,
        account_type: str,
    ) -> Optional[CryptoCustodyAccount]:
        return (
            db.query(CryptoCustodyAccount)
            .filter(
                CryptoCustodyAccount.asset == asset,
                CryptoCustodyAccount.account_type == account_type,
                CryptoCustodyAccount.status == "active",
            )
            .first()
        )

    @staticmethod
    def get_or_create_account(
        db: Session,
        asset: str,
        account_type: str,
        provider: str = DEFAULT_PROVIDER,
        label: Optional[str] = None,
    ) -> CryptoCustodyAccount:
        existing = CryptoCustodyAccountRepository.get_by_asset_and_type(db, asset, account_type)
        if existing:
            return existing
        if label is None:
            type_label = "Clients Pool" if account_type == ACCOUNT_TYPE_CLIENTS_POOL else "Settlement Wallet"
            label = f"{type_label} {asset}"
        acc = CryptoCustodyAccount(
            asset=asset,
            account_type=account_type,
            provider=provider,
            label=label,
            status="active",
        )
        db.add(acc)
        db.flush()
        return acc

    @staticmethod
    def list_accounts(db: Session) -> list[CryptoCustodyAccount]:
        return (
            db.query(CryptoCustodyAccount)
            .filter(CryptoCustodyAccount.status == "active")
            .order_by(CryptoCustodyAccount.asset, CryptoCustodyAccount.account_type)
            .all()
        )

    @staticmethod
    def list_accounts_by_asset(db: Session, asset: str) -> list[CryptoCustodyAccount]:
        return (
            db.query(CryptoCustodyAccount)
            .filter(CryptoCustodyAccount.asset == asset, CryptoCustodyAccount.status == "active")
            .order_by(CryptoCustodyAccount.account_type)
            .all()
        )


class CryptoCustodyBalanceRepository:
    @staticmethod
    def get_balance(db: Session, account_id: UUID) -> Optional[CryptoCustodyBalance]:
        return (
            db.query(CryptoCustodyBalance)
            .filter(CryptoCustodyBalance.account_id == account_id)
            .first()
        )

    @staticmethod
    def get_or_create_balance(
        db: Session,
        account_id: UUID,
        asset: str,
    ) -> CryptoCustodyBalance:
        bal = CryptoCustodyBalanceRepository.get_balance(db, account_id)
        if bal:
            return bal
        bal = CryptoCustodyBalance(
            account_id=account_id,
            asset=asset,
            actual_balance=Decimal("0"),
            expected_balance=Decimal("0"),
        )
        db.add(bal)
        db.flush()
        return bal

    @staticmethod
    def update_expected_balance(
        db: Session,
        account_id: UUID,
        *,
        amount_delta: Optional[Decimal] = None,
        absolute: Optional[Decimal] = None,
    ) -> CryptoCustodyBalance:
        bal = CryptoCustodyBalanceRepository.get_balance(db, account_id)
        if not bal:
            raise ValueError(f"No balance for account_id={account_id}")
        if absolute is not None:
            bal.expected_balance = absolute
        elif amount_delta is not None:
            bal.expected_balance = Decimal(str(bal.expected_balance)) + amount_delta
        db.flush()
        return bal

    @staticmethod
    def update_actual_balance(
        db: Session,
        account_id: UUID,
        absolute_balance: Decimal,
        provider_timestamp: Optional[datetime] = None,
    ) -> CryptoCustodyBalance:
        bal = CryptoCustodyBalanceRepository.get_balance(db, account_id)
        if not bal:
            raise ValueError(f"No balance for account_id={account_id}")
        bal.actual_balance = absolute_balance
        if provider_timestamp is not None:
            bal.updated_from_provider_at = provider_timestamp
        db.flush()
        return bal
