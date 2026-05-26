"""Repositories for Privy user-wallet ledger."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from database import PersonCryptoWallet

from .enums import PersonWalletDepositStatus, PrivyWebhookEventStatus
from .models import PersonWalletBalance, PersonWalletDeposit, PrivyWebhookEvent


class PrivyWebhookEventRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> PrivyWebhookEvent:
        event = PrivyWebhookEvent(**data)
        db.add(event)
        db.flush()
        return event

    @staticmethod
    def get_by_id(db: Session, event_id: UUID) -> PrivyWebhookEvent | None:
        return db.query(PrivyWebhookEvent).filter(PrivyWebhookEvent.id == event_id).first()

    @staticmethod
    def find_by_idempotency_key(db: Session, key: str) -> PrivyWebhookEvent | None:
        return (
            db.query(PrivyWebhookEvent)
            .filter(PrivyWebhookEvent.idempotency_key == key)
            .order_by(PrivyWebhookEvent.received_at.desc())
            .first()
        )

    @staticmethod
    def find_by_svix_id(db: Session, svix_id: str) -> PrivyWebhookEvent | None:
        return (
            db.query(PrivyWebhookEvent)
            .filter(PrivyWebhookEvent.svix_id == svix_id)
            .first()
        )

    @staticmethod
    def update_status(
        db: Session,
        event: PrivyWebhookEvent,
        *,
        status: str,
        error_message: str | None = None,
        linked_deposit_id: UUID | None = None,
    ) -> PrivyWebhookEvent:
        event.processing_status = status
        if error_message is not None:
            event.error_message = error_message
        if linked_deposit_id is not None:
            event.linked_deposit_id = linked_deposit_id
        if status in (
            PrivyWebhookEventStatus.PROCESSED.value,
            PrivyWebhookEventStatus.FAILED.value,
            PrivyWebhookEventStatus.IGNORED.value,
            PrivyWebhookEventStatus.DUPLICATE.value,
        ):
            event.processed_at = datetime.now(timezone.utc)
        db.add(event)
        db.flush()
        return event


class PersonWalletDepositRepository:

    @staticmethod
    def find_by_chain_tx(
        db: Session,
        *,
        chain_id: int | None,
        tx_hash: str,
        log_index: int,
    ) -> PersonWalletDeposit | None:
        normalized_hash = str(tx_hash or "").strip().lower()
        q = db.query(PersonWalletDeposit).filter(
            PersonWalletDeposit.tx_hash == normalized_hash,
            PersonWalletDeposit.log_index == log_index,
        )
        if chain_id is not None:
            q = q.filter(PersonWalletDeposit.chain_id == chain_id)
        return q.first()

    @staticmethod
    def find_confirmed_by_tx_hash(
        db: Session,
        *,
        tx_hash: str,
        wallet_id: UUID | None = None,
        person_id: UUID | None = None,
    ) -> list[PersonWalletDeposit]:
        normalized_hash = str(tx_hash or "").strip().lower()
        q = db.query(PersonWalletDeposit).filter(
            PersonWalletDeposit.tx_hash == normalized_hash,
            PersonWalletDeposit.status == PersonWalletDepositStatus.CONFIRMED.value,
        )
        if wallet_id is not None:
            q = q.filter(PersonWalletDeposit.person_crypto_wallet_id == wallet_id)
        if person_id is not None:
            q = q.filter(PersonWalletDeposit.person_id == person_id)
        return q.order_by(PersonWalletDeposit.created_at.asc()).all()

    @staticmethod
    def create(db: Session, *, data: dict) -> PersonWalletDeposit:
        row = PersonWalletDeposit(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def list_for_person(
        db: Session,
        person_id: UUID,
        *,
        asset: str | None = None,
        limit: int = 100,
    ) -> list[PersonWalletDeposit]:
        q = (
            db.query(PersonWalletDeposit)
            .filter(PersonWalletDeposit.person_id == person_id)
            .order_by(PersonWalletDeposit.created_at.desc())
        )
        if asset:
            q = q.filter(PersonWalletDeposit.asset == asset.upper())
        return q.limit(limit).all()

    @staticmethod
    def get_for_person(
        db: Session,
        deposit_id: UUID,
        person_id: UUID,
    ) -> PersonWalletDeposit | None:
        return (
            db.query(PersonWalletDeposit)
            .filter(
                PersonWalletDeposit.id == deposit_id,
                PersonWalletDeposit.person_id == person_id,
            )
            .first()
        )


class PersonWalletBalanceRepository:

    @staticmethod
    def get_or_create_for_update(
        db: Session,
        *,
        wallet_id: UUID,
        person_id: UUID,
        asset: str,
    ) -> PersonWalletBalance:
        row = (
            db.query(PersonWalletBalance)
            .filter(
                PersonWalletBalance.person_crypto_wallet_id == wallet_id,
                PersonWalletBalance.asset == asset.upper(),
            )
            .with_for_update()
            .first()
        )
        if row is not None:
            return row

        row = PersonWalletBalance(
            person_crypto_wallet_id=wallet_id,
            person_id=person_id,
            asset=asset.upper(),
            balance=Decimal("0"),
            available_balance=Decimal("0"),
            sync_source="privy_webhook",
        )
        db.add(row)
        db.flush()
        return (
            db.query(PersonWalletBalance)
            .filter(PersonWalletBalance.id == row.id)
            .with_for_update()
            .first()
        )

    @staticmethod
    def increment_balance(
        db: Session,
        balance: PersonWalletBalance,
        *,
        delta: Decimal,
        sync_source: str = "privy_webhook",
    ) -> PersonWalletBalance:
        balance.balance = Decimal(str(balance.balance)) + delta
        balance.available_balance = Decimal(str(balance.available_balance)) + delta
        balance.sync_source = sync_source
        balance.last_synced_at = datetime.now(timezone.utc)
        db.add(balance)
        db.flush()
        return balance

    @staticmethod
    def list_for_person(db: Session, person_id: UUID) -> list[PersonWalletBalance]:
        return (
            db.query(PersonWalletBalance)
            .filter(PersonWalletBalance.person_id == person_id)
            .order_by(PersonWalletBalance.asset.asc())
            .all()
        )


class PersonCryptoWalletRepository:

    @staticmethod
    def find_active_by_address(
        db: Session,
        address: str,
        *,
        provider: str = "privy",
    ) -> PersonCryptoWallet | None:
        from services.privy_wallet.asset_mapping import normalize_evm_address

        normalized = normalize_evm_address(address)
        if not normalized:
            return None
        return (
            db.query(PersonCryptoWallet)
            .filter(
                PersonCryptoWallet.provider == provider,
                PersonCryptoWallet.revoked_at.is_(None),
                PersonCryptoWallet.address.ilike(normalized),
            )
            .first()
        )

    @staticmethod
    def list_active_for_person(db: Session, person_id: UUID) -> list[PersonCryptoWallet]:
        return (
            db.query(PersonCryptoWallet)
            .filter(
                PersonCryptoWallet.person_id == person_id,
                PersonCryptoWallet.revoked_at.is_(None),
            )
            .order_by(PersonCryptoWallet.is_primary.desc(), PersonCryptoWallet.created_at.asc())
            .all()
        )
