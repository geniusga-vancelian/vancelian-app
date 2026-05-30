"""Webhook processing for Privy ``wallet.funds_deposited`` events."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.hashing import compute_request_hash
from services.test_clients.schemas import ASSET_NAMES

from .asset_mapping import (
    format_amount_display,
    normalize_evm_address,
    parse_amount_to_decimal,
    parse_caip2_chain_id,
    resolve_asset_symbol,
)
from .enums import (
    PersonWalletDepositStatus,
    PersonWalletDirection,
    PersonWalletTransactionKind,
    PrivyWebhookEventStatus,
)
from .models import PersonWalletDeposit, PrivyWebhookEvent
from .repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
    PrivyWebhookEventRepository,
)

logger = logging.getLogger(__name__)

FUNDS_DEPOSITED_EVENT = "wallet.funds_deposited"


@dataclass(frozen=True)
class NormalizedPrivyDeposit:
    to_address: str
    from_address: str | None
    asset: str
    amount: Decimal
    chain_type: str
    chain_id: int | None
    tx_hash: str
    log_index: int
    block_number: int | None
    confirmations: int


class PrivyWebhookProcessor:

    def __init__(self) -> None:
        self._event_repo = PrivyWebhookEventRepository()
        self._deposit_repo = PersonWalletDepositRepository()
        self._balance_repo = PersonWalletBalanceRepository()
        self._wallet_repo = PersonCryptoWalletRepository()

    def store_raw_event(
        self,
        db: Session,
        *,
        event_type: str,
        payload: dict[str, Any],
        svix_id: str | None,
        idempotency_key: str | None,
        external_reference: str | None,
    ) -> PrivyWebhookEvent:
        payload_hash = compute_request_hash(payload)
        dedupe_key = idempotency_key or svix_id

        if dedupe_key:
            existing = self._event_repo.find_by_idempotency_key(db, dedupe_key)
            if existing is None and svix_id:
                existing = self._event_repo.find_by_svix_id(db, svix_id)
            if existing:
                if existing.processing_status in (
                    PrivyWebhookEventStatus.PROCESSED.value,
                    PrivyWebhookEventStatus.DUPLICATE.value,
                ) and existing.payload_hash == payload_hash:
                    existing.retry_count = (existing.retry_count or 0) + 1
                    self._event_repo.update_status(
                        db, existing, status=PrivyWebhookEventStatus.DUPLICATE.value
                    )
                    return existing

                existing.payload_raw = payload
                existing.payload_hash = payload_hash
                existing.event_type = event_type
                existing.external_reference = external_reference
                existing.error_message = None
                existing.retry_count = (existing.retry_count or 0) + 1
                self._event_repo.update_status(
                    db, existing, status=PrivyWebhookEventStatus.RECEIVED.value
                )
                return existing

        try:
            event = self._event_repo.create(
                db,
                data={
                    "svix_id": svix_id,
                    "idempotency_key": dedupe_key,
                    "event_type": event_type,
                    "external_reference": external_reference,
                    "payload_raw": payload,
                    "payload_hash": payload_hash,
                    "processing_status": PrivyWebhookEventStatus.RECEIVED.value,
                },
            )
        except Exception as exc:
            if svix_id and "uq_privy_webhook_events_svix_id" in str(exc):
                db.rollback()
                existing = self._event_repo.find_by_svix_id(db, svix_id)
                if existing is None:
                    raise
                existing.payload_raw = payload
                existing.payload_hash = payload_hash
                existing.event_type = event_type
                existing.external_reference = external_reference
                existing.error_message = None
                existing.retry_count = (existing.retry_count or 0) + 1
                self._event_repo.update_status(
                    db, existing, status=PrivyWebhookEventStatus.RECEIVED.value
                )
                return existing
            raise
        return event

    def process_event(self, db: Session, event: PrivyWebhookEvent) -> str:
        if event.processing_status in (
            PrivyWebhookEventStatus.PROCESSED.value,
            PrivyWebhookEventStatus.DUPLICATE.value,
        ):
            return event.processing_status

        self._event_repo.update_status(
            db, event, status=PrivyWebhookEventStatus.PROCESSING.value
        )

        if event.event_type != FUNDS_DEPOSITED_EVENT:
            self._event_repo.update_status(
                db,
                event,
                status=PrivyWebhookEventStatus.IGNORED.value,
                error_message=f"Unsupported event type: {event.event_type}",
            )
            return PrivyWebhookEventStatus.IGNORED.value

        try:
            deposit = self._handle_funds_deposited(db, event)
            self._event_repo.update_status(
                db,
                event,
                status=PrivyWebhookEventStatus.PROCESSED.value,
                linked_deposit_id=deposit.id if deposit else None,
            )
            return PrivyWebhookEventStatus.PROCESSED.value
        except Exception as exc:
            logger.exception("Privy webhook processing failed for event %s", event.id)
            self._event_repo.update_status(
                db,
                event,
                status=PrivyWebhookEventStatus.FAILED.value,
                error_message=str(exc)[:2000],
            )
            return PrivyWebhookEventStatus.FAILED.value

    def _handle_funds_deposited(
        self,
        db: Session,
        event: PrivyWebhookEvent,
    ) -> PersonWalletDeposit | None:
        normalized = self._normalize_deposit_payload(event.payload_raw)
        wallet = self._wallet_repo.find_active_by_address(db, normalized.to_address)
        if wallet is None:
            raise ValueError(f"Unknown wallet address: {normalized.to_address}")

        existing = self._deposit_repo.find_by_chain_tx(
            db,
            chain_id=normalized.chain_id,
            tx_hash=normalized.tx_hash,
            log_index=normalized.log_index,
        )
        if existing:
            self._classify_observed_external_deposit(db, existing, event=event)
            return existing

        for prior in self._deposit_repo.find_confirmed_by_tx_hash(
            db,
            tx_hash=normalized.tx_hash,
            wallet_id=wallet.id,
        ):
            if prior.asset.upper() == normalized.asset.upper():
                self._classify_observed_external_deposit(db, prior, event=event)
                return prior

        asset_name = ASSET_NAMES.get(normalized.asset, normalized.asset)
        amount_display = format_amount_display(normalized.amount, normalized.asset)
        title = f"Dépôt {asset_name}"
        subtitle = f"+{amount_display} {normalized.asset}"

        deposit = self._deposit_repo.create(
            db,
            data={
                "person_crypto_wallet_id": wallet.id,
                "person_id": wallet.person_id,
                "pe_client_id": wallet.pe_client_id,
                "privy_webhook_event_id": event.id,
                "transaction_kind": PersonWalletTransactionKind.PRIVY_DEPOSIT_IN.value,
                "direction": PersonWalletDirection.CREDIT.value,
                "asset": normalized.asset,
                "amount": normalized.amount,
                "chain_type": normalized.chain_type,
                "chain_id": normalized.chain_id,
                "tx_hash": normalized.tx_hash,
                "log_index": normalized.log_index,
                "block_number": normalized.block_number,
                "from_address": normalized.from_address,
                "to_address": normalized.to_address,
                "confirmations": normalized.confirmations,
                "status": PersonWalletDepositStatus.CONFIRMED.value,
                "idempotency_key": event.idempotency_key,
                "title": title,
                "subtitle": subtitle,
                "metadata_json": {
                    "privy_event_type": event.event_type,
                    **self._observed_external_deposit_metadata(event),
                },
                "confirmed_at": datetime.now(timezone.utc),
            },
        )

        balance = self._balance_repo.get_or_create_for_update(
            db,
            wallet_id=wallet.id,
            person_id=wallet.person_id,
            asset=normalized.asset,
        )
        self._balance_repo.increment_balance(db, balance, delta=normalized.amount)
        self._classify_observed_external_deposit(db, deposit, event=event)
        return deposit

    @staticmethod
    def _observed_external_deposit_metadata(event: PrivyWebhookEvent) -> dict[str, Any]:
        from services.transaction_intents.privy_deposit_intent_sync import (
            build_observed_external_deposit_classification,
        )

        return build_observed_external_deposit_classification(
            privy_webhook_event_id=event.id,
        )

    @staticmethod
    def _classify_observed_external_deposit(
        db: Session,
        deposit: PersonWalletDeposit,
        *,
        event: PrivyWebhookEvent,
    ) -> None:
        try:
            from services.transaction_intents.privy_deposit_intent_sync import (
                classify_observed_external_privy_deposit,
            )

            classify_observed_external_privy_deposit(
                db,
                deposit,
                privy_webhook_event_id=event.id,
            )
        except Exception:
            logger.warning(
                "privy_deposit.observation_failed",
                extra={"deposit_id": str(deposit.id)},
                exc_info=True,
            )

    @staticmethod
    def _normalize_deposit_payload(payload: dict[str, Any]) -> NormalizedPrivyDeposit:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

        to_address = (
            data.get("to_address")
            or data.get("recipient")
            or _deep_get(data, "wallet", "address")
            or _deep_get(data, "wallet", "wallet_address")
        )
        to_address = normalize_evm_address(to_address)
        if not to_address:
            raise ValueError("Missing recipient address in webhook payload")

        from_address = normalize_evm_address(
            data.get("from_address") or data.get("sender")
        )

        chain_id = parse_caip2_chain_id(
            data.get("chain_id") or data.get("caip2") or data.get("chain")
        )
        chain_type = "ethereum"
        if chain_id is not None:
            chain_type = "ethereum"

        contract = normalize_evm_address(
            data.get("contract_address")
            or _deep_get(data, "asset", "contract_address")
            or _deep_get(data, "token", "address")
        )
        asset = resolve_asset_symbol(
            chain_id=chain_id,
            asset_payload=data.get("asset") or data.get("token"),
            contract_address=contract,
        )
        if not asset:
            raise ValueError("Unable to resolve asset symbol from webhook payload")

        amount_raw = (
            data.get("amount")
            or data.get("value")
            or _deep_get(data, "asset", "amount")
            or _deep_get(data, "transfer", "amount")
        )
        amount = parse_amount_to_decimal(amount_raw, asset)

        tx_hash = (
            data.get("transaction_hash")
            or data.get("tx_hash")
            or data.get("hash")
            or _deep_get(data, "transaction", "hash")
        )
        if not tx_hash:
            raise ValueError("Missing transaction hash in webhook payload")
        tx_hash = str(tx_hash).strip().lower()
        if not tx_hash.startswith("0x"):
            tx_hash = f"0x{tx_hash}"

        log_index_raw = (
            data.get("log_index")
            or data.get("transaction_index")
            or _deep_get(data, "transaction", "log_index")
            or 0
        )
        log_index = int(log_index_raw)

        block_number_raw = data.get("block_number") or _deep_get(data, "transaction", "block_number")
        block_number = int(block_number_raw) if block_number_raw is not None else None

        confirmations_raw = data.get("confirmations") or data.get("confirmation_count") or 1
        confirmations = int(confirmations_raw)

        return NormalizedPrivyDeposit(
            to_address=to_address,
            from_address=from_address,
            asset=asset.upper(),
            amount=amount,
            chain_type=chain_type,
            chain_id=chain_id,
            tx_hash=tx_hash,
            log_index=log_index,
            block_number=block_number,
            confirmations=confirmations,
        )


def _deep_get(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur
