"""Webhook processing engine for custody BAS webhooks.

Three-layer architecture:
  1. Raw storage   — persist the webhook payload before any business logic
  2. Normalization — convert BAS-specific format to internal NormalizedEventType
  3. Application   — execute the business logic (create tx, post ledger, update balance)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.hashing import compute_request_hash
from services.portfolio_engine.ledger_accounts.models import LedgerAccount
from services.portfolio_engine.ledger_entries.service import LedgerEntryService

from .enums import (
    NormalizedEventType,
    TransactionDirection,
    TransactionKind,
    TransactionStatus,
    TransactionType,
    WebhookEventStatus,
)
from .models import CustodyWebhookEvent
from .repository import (
    CustodyAccountRepository,
    CustodyBalanceRepository,
    CustodyProviderRepository,
    CustodyTransactionRepository,
    CustodyWebhookEventRepository,
)
from .state_machine import InvalidTransitionError, validate_transition

logger = logging.getLogger(__name__)

_EVENT_TYPE_MAP: dict[str, NormalizedEventType] = {
    "deposit": NormalizedEventType.DEPOSIT_DETECTED,
    "deposit_detected": NormalizedEventType.DEPOSIT_DETECTED,
    "withdrawal_requested": NormalizedEventType.WITHDRAWAL_REQUESTED,
    "withdrawal_completed": NormalizedEventType.WITHDRAWAL_COMPLETED,
    "withdrawal_failed": NormalizedEventType.WITHDRAWAL_FAILED,
    "internal_transfer_completed": NormalizedEventType.INTERNAL_TRANSFER_COMPLETED,
    "reversal": NormalizedEventType.REVERSAL_DETECTED,
    "reversal_detected": NormalizedEventType.REVERSAL_DETECTED,
}


class WebhookProcessor:

    def __init__(self) -> None:
        self._provider_repo = CustodyProviderRepository()
        self._account_repo = CustodyAccountRepository()
        self._balance_repo = CustodyBalanceRepository()
        self._tx_repo = CustodyTransactionRepository()
        self._event_repo = CustodyWebhookEventRepository()
        self._ledger_svc = LedgerEntryService()

    # ── Layer 1 : Raw storage ─────────────────────────────────────────

    def store_raw_event(
        self,
        db: Session,
        *,
        provider_id: UUID,
        event_type: str,
        external_reference: str | None,
        payload: dict,
    ) -> CustodyWebhookEvent:
        """Persist the raw webhook before any normalisation."""
        payload_hash = compute_request_hash(payload)

        if external_reference:
            existing = self._event_repo.find_by_provider_and_ref(
                db, provider_id, external_reference
            )
            if existing and existing.processing_status in (
                WebhookEventStatus.PROCESSED.value,
                WebhookEventStatus.DUPLICATE.value,
            ):
                if existing.payload_hash == payload_hash:
                    existing.retry_count += 1
                    self._event_repo.update_status(
                        db, existing, status=WebhookEventStatus.DUPLICATE.value
                    )
                    return existing
                else:
                    new_event = self._event_repo.create(
                        db,
                        data={
                            "provider_id": provider_id,
                            "event_type": event_type,
                            "external_reference": external_reference,
                            "payload_raw": payload,
                            "payload_hash": payload_hash,
                            "processing_status": WebhookEventStatus.FAILED.value,
                            "error_message": (
                                "Same external_reference with different payload — "
                                f"expected hash {existing.payload_hash}, got {payload_hash}"
                            ),
                        },
                    )
                    return new_event

        event = self._event_repo.create(
            db,
            data={
                "provider_id": provider_id,
                "event_type": event_type,
                "external_reference": external_reference,
                "payload_raw": payload,
                "payload_hash": payload_hash,
                "processing_status": WebhookEventStatus.RECEIVED.value,
            },
        )
        return event

    # ── Layer 2 : Normalization ───────────────────────────────────────

    @staticmethod
    def normalize_event_type(raw_event_type: str) -> NormalizedEventType | None:
        return _EVENT_TYPE_MAP.get(raw_event_type.lower())

    # ── Layer 3 : Business logic application ──────────────────────────

    def process_event(
        self,
        db: Session,
        event: CustodyWebhookEvent,
        *,
        is_replay: bool = False,
    ) -> str:
        """Process a stored webhook event. Returns the final processing_status."""

        if event.processing_status in (
            WebhookEventStatus.PROCESSED.value,
            WebhookEventStatus.DUPLICATE.value,
        ) and not is_replay:
            return event.processing_status

        self._event_repo.update_status(
            db, event, status=WebhookEventStatus.PROCESSING.value
        )

        normalized = self.normalize_event_type(event.event_type)
        if normalized is None:
            self._event_repo.update_status(
                db,
                event,
                status=WebhookEventStatus.IGNORED.value,
                error_message=f"Unknown event type: {event.event_type}",
            )
            return WebhookEventStatus.IGNORED.value

        try:
            handler = _EVENT_HANDLERS.get(normalized)
            if handler is None:
                self._event_repo.update_status(
                    db,
                    event,
                    status=WebhookEventStatus.IGNORED.value,
                    error_message=f"No handler for {normalized.value}",
                )
                return WebhookEventStatus.IGNORED.value

            tx = handler(self, db, event)
            self._event_repo.update_status(
                db,
                event,
                status=WebhookEventStatus.PROCESSED.value,
                linked_transaction_id=tx.id if tx else None,
            )
            return WebhookEventStatus.PROCESSED.value

        except Exception as exc:
            logger.exception("Webhook processing failed for event %s", event.id)
            self._event_repo.update_status(
                db,
                event,
                status=WebhookEventStatus.FAILED.value,
                error_message=str(exc)[:2000],
            )
            return WebhookEventStatus.FAILED.value

    # ── Handlers per event type ───────────────────────────────────────

    def _handle_deposit(self, db: Session, event: CustodyWebhookEvent):
        payload = event.payload_raw
        iban = payload.get("iban") or payload.get("account_iban")
        amount_raw = payload.get("amount")
        currency = payload.get("currency", "EUR")

        if not iban:
            raise ValueError("Missing iban in webhook payload")
        if amount_raw is None:
            raise ValueError("Missing amount in webhook payload")

        try:
            amount = Decimal(str(amount_raw))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid amount: {amount_raw}")

        account = self._account_repo.find_by_iban(db, iban)
        if account is None:
            raise ValueError(f"Unknown IBAN: {iban}")

        if account.currency != currency:
            raise ValueError(
                f"Currency mismatch: account={account.currency}, webhook={currency}"
            )

        existing_tx = self._tx_repo.find_by_provider_and_ref(
            db, event.provider_id, event.external_reference
        )
        if existing_tx:
            return existing_tx

        settlement = self._account_repo.find_settlement_account(db, currency)

        tx_metadata = {"webhook_event_id": str(event.id)}
        for key in (
            "remitter_name", "remitter_iban", "remitter_bank_name",
            "account_holder_name", "booking_date", "value_date", "narrative",
        ):
            val = payload.get(key)
            if val is not None:
                tx_metadata[key] = val

        tx = self._tx_repo.create(
            db,
            data={
                "account_id": account.id,
                "provider_id": event.provider_id,
                "transaction_type": TransactionType.DEPOSIT.value,
                "transaction_kind": TransactionKind.BANK_TRANSFER_IN.value,
                "direction": TransactionDirection.CREDIT.value,
                "amount": amount,
                "currency": currency,
                "status": TransactionStatus.PENDING.value,
                "external_reference": event.external_reference,
                "metadata_": tx_metadata,
            },
        )

        validate_transition(tx.status, TransactionStatus.PROCESSING.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.PROCESSING.value)

        balance = self._balance_repo.get_for_update(db, account.id)
        self._balance_repo.update_balance(db, balance, delta=amount)

        if account.ledger_account_id and settlement and settlement.ledger_account_id:
            self._ledger_svc.post_double_entry(
                db,
                debit_account_id=account.ledger_account_id,
                credit_account_id=settlement.ledger_account_id,
                amount=amount,
                currency=currency,
                reference_type="custody_transaction",
                reference_id=tx.id,
                effective_at=datetime.now(timezone.utc),
                description=f"BAS deposit {currency} {amount}",
                metadata={"webhook_event_id": str(event.id)},
            )

        validate_transition(tx.status, TransactionStatus.COMPLETED.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.COMPLETED.value)
        return tx

    def _handle_withdrawal_requested(self, db: Session, event: CustodyWebhookEvent):
        payload = event.payload_raw
        iban = payload.get("iban") or payload.get("account_iban")
        amount_raw = payload.get("amount")
        currency = payload.get("currency", "EUR")

        if not iban or amount_raw is None:
            raise ValueError("Missing iban or amount in webhook payload")

        amount = Decimal(str(amount_raw))
        account = self._account_repo.find_by_iban(db, iban)
        if account is None:
            raise ValueError(f"Unknown IBAN: {iban}")
        if account.currency != currency:
            raise ValueError(
                f"Currency mismatch: account={account.currency}, webhook={currency}"
            )

        existing_tx = self._tx_repo.find_by_provider_and_ref(
            db, event.provider_id, event.external_reference
        )
        if existing_tx:
            return existing_tx

        balance = self._balance_repo.get_for_update(db, account.id)
        current = Decimal(str(balance.available_balance))
        if current < amount:
            raise ValueError(
                f"Insufficient funds: available={current}, requested={amount}"
            )

        tx = self._tx_repo.create(
            db,
            data={
                "account_id": account.id,
                "provider_id": event.provider_id,
                "transaction_type": TransactionType.WITHDRAWAL.value,
                "transaction_kind": TransactionKind.BANK_TRANSFER_OUT.value,
                "direction": TransactionDirection.DEBIT.value,
                "amount": amount,
                "currency": currency,
                "status": TransactionStatus.PENDING.value,
                "external_reference": event.external_reference,
                "metadata_": {"webhook_event_id": str(event.id)},
            },
        )
        return tx

    def _handle_withdrawal_completed(self, db: Session, event: CustodyWebhookEvent):
        payload = event.payload_raw
        ext_ref = payload.get("original_reference") or event.external_reference
        currency = payload.get("currency", "EUR")

        tx = self._tx_repo.find_by_provider_and_ref(db, event.provider_id, ext_ref)
        if tx is None:
            raise ValueError(f"No pending withdrawal found for reference: {ext_ref}")

        if tx.status == TransactionStatus.COMPLETED.value:
            return tx

        validate_transition(tx.status, TransactionStatus.PROCESSING.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.PROCESSING.value)

        account = self._account_repo.get_by_id(db, tx.account_id)
        settlement = self._account_repo.find_settlement_account(db, currency)
        balance = self._balance_repo.get_for_update(db, account.id)
        self._balance_repo.update_balance(db, balance, delta=-tx.amount)

        if account.ledger_account_id and settlement and settlement.ledger_account_id:
            self._ledger_svc.post_double_entry(
                db,
                debit_account_id=settlement.ledger_account_id,
                credit_account_id=account.ledger_account_id,
                amount=tx.amount,
                currency=currency,
                reference_type="custody_transaction",
                reference_id=tx.id,
                effective_at=datetime.now(timezone.utc),
                description=f"BAS withdrawal completed {currency} {tx.amount}",
                metadata={"webhook_event_id": str(event.id)},
            )

        validate_transition(tx.status, TransactionStatus.COMPLETED.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.COMPLETED.value)
        return tx

    def _handle_withdrawal_failed(self, db: Session, event: CustodyWebhookEvent):
        payload = event.payload_raw
        ext_ref = payload.get("original_reference") or event.external_reference
        reason = payload.get("reason", "BAS withdrawal failed")

        tx = self._tx_repo.find_by_provider_and_ref(db, event.provider_id, ext_ref)
        if tx is None:
            raise ValueError(f"No pending withdrawal found for reference: {ext_ref}")

        if tx.status in (TransactionStatus.FAILED.value, TransactionStatus.REVERSED.value):
            return tx

        validate_transition(tx.status, TransactionStatus.FAILED.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.FAILED.value, failure_reason=reason)
        return tx

    def _handle_reversal(self, db: Session, event: CustodyWebhookEvent):
        payload = event.payload_raw
        original_ref = payload.get("original_reference") or payload.get("reversed_reference")
        currency = payload.get("currency", "EUR")

        if not original_ref:
            raise ValueError("Missing original_reference for reversal")

        original_tx = self._tx_repo.find_by_provider_and_ref(
            db, event.provider_id, original_ref
        )
        if original_tx is None:
            raise ValueError(f"Original transaction not found for reference: {original_ref}")

        if original_tx.status == TransactionStatus.REVERSED.value:
            return original_tx

        validate_transition(original_tx.status, TransactionStatus.REVERSED.value)

        account = self._account_repo.get_by_id(db, original_tx.account_id)
        settlement = self._account_repo.find_settlement_account(db, currency)

        if original_tx.direction == TransactionDirection.CREDIT.value:
            delta = -original_tx.amount
        else:
            delta = original_tx.amount

        balance = self._balance_repo.get_for_update(db, account.id)
        self._balance_repo.update_balance(db, balance, delta=delta)

        if account.ledger_account_id and settlement and settlement.ledger_account_id:
            if original_tx.direction == TransactionDirection.CREDIT.value:
                debit_id = settlement.ledger_account_id
                credit_id = account.ledger_account_id
            else:
                debit_id = account.ledger_account_id
                credit_id = settlement.ledger_account_id

            self._ledger_svc.post_double_entry(
                db,
                debit_account_id=debit_id,
                credit_account_id=credit_id,
                amount=original_tx.amount,
                currency=currency,
                reference_type="custody_reversal",
                reference_id=original_tx.id,
                effective_at=datetime.now(timezone.utc),
                description=f"Reversal of {original_tx.transaction_type} {currency} {original_tx.amount}",
                metadata={
                    "webhook_event_id": str(event.id),
                    "original_transaction_id": str(original_tx.id),
                },
            )

        reversal_tx = self._tx_repo.create(
            db,
            data={
                "account_id": original_tx.account_id,
                "provider_id": event.provider_id,
                "transaction_type": original_tx.transaction_type,
                "direction": TransactionDirection.DEBIT.value
                if original_tx.direction == TransactionDirection.CREDIT.value
                else TransactionDirection.CREDIT.value,
                "amount": original_tx.amount,
                "currency": currency,
                "status": TransactionStatus.COMPLETED.value,
                "external_reference": event.external_reference,
                "reversal_of_transaction_id": original_tx.id,
                "metadata_": {
                    "webhook_event_id": str(event.id),
                    "original_transaction_id": str(original_tx.id),
                },
            },
        )

        self._tx_repo.update_status(
            db, original_tx, new_status=TransactionStatus.REVERSED.value
        )
        return reversal_tx


_EVENT_HANDLERS: dict = {
    NormalizedEventType.DEPOSIT_DETECTED: WebhookProcessor._handle_deposit,
    NormalizedEventType.WITHDRAWAL_REQUESTED: WebhookProcessor._handle_withdrawal_requested,
    NormalizedEventType.WITHDRAWAL_COMPLETED: WebhookProcessor._handle_withdrawal_completed,
    NormalizedEventType.WITHDRAWAL_FAILED: WebhookProcessor._handle_withdrawal_failed,
    NormalizedEventType.REVERSAL_DETECTED: WebhookProcessor._handle_reversal,
}
