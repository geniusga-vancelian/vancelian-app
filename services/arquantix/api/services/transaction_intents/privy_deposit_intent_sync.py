"""Dépôts Privy — classification observée vs intent webapp (Phase 1 corrigée).

Doctrine :
- Dépôt externe (webhook Privy) = événement observé, pas une intention portail.
- ``transaction_intent`` réservé aux actions initiées dans la webapp Vancelian.
- Un intent ``PRIVY_DEPOSIT`` ne peut exister que via un futur parcours webapp explicite
  (``ensure_webapp_privy_deposit_intent(..., webapp_initiated=True)``).
"""
from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.privy_wallet.enums import PersonWalletDepositStatus

from .enums import IntentOperationType, IntentProductType, IntentStatus
from .raw_event_link import try_link_raw_event_to_intent
from .repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

PRIVY_DEPOSIT_LINKED_TABLE = "person_wallet_deposits"
PRIVY_DEPOSIT_PRODUCT = IntentProductType.PRIVY_DEPOSIT.value

OBSERVED_EXTERNAL_DEPOSIT_KEY = "observed_external_deposit"
DEFAULT_RAW_EVENT_TTL_HOURS = 24


def privy_deposit_raw_event_ttl_hours() -> int:
    raw = os.getenv("PRIVY_DEPOSIT_RAW_EVENT_TTL_HOURS", str(DEFAULT_RAW_EVENT_TTL_HOURS)).strip()
    if raw.isdigit():
        return max(1, int(raw))
    return DEFAULT_RAW_EVENT_TTL_HOURS


def build_observed_external_deposit_classification(
    *,
    privy_webhook_event_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Métadonnées neutres pour un dépôt inbound externe (sans intent)."""
    meta: dict[str, Any] = {
        OBSERVED_EXTERNAL_DEPOSIT_KEY: True,
        "event_source": "privy_webhook",
        "initiated_by": "external",
        "transaction_intent_policy": "none_by_default",
    }
    if privy_webhook_event_id is not None:
        meta["privy_webhook_event_id"] = str(privy_webhook_event_id)
    return meta


def classify_observed_external_privy_deposit(
    db: Session,
    deposit,
    *,
    privy_webhook_event_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Classifie un dépôt Privy webhook — best-effort, n'écrit pas d'intent."""
    if deposit is None:
        return {}

    classification = build_observed_external_deposit_classification(
        privy_webhook_event_id=privy_webhook_event_id or getattr(deposit, "privy_webhook_event_id", None),
    )
    try:
        base = deposit.metadata_json if isinstance(deposit.metadata_json, dict) else {}
        merged = {**base, **classification}
        if merged != base:
            deposit.metadata_json = merged
            db.add(deposit)
            db.flush()
        logger.debug(
            "privy_deposit.observed_external",
            extra={
                "deposit_id": str(getattr(deposit, "id", "")),
                "person_id": str(getattr(deposit, "person_id", "")),
            },
        )
    except Exception as exc:
        logger.warning(
            "privy_deposit.classification_failed",
            extra={"deposit_id": str(getattr(deposit, "id", "")), "error": str(exc)},
        )
    return classification


def privy_deposit_intent_key(deposit_id: UUID) -> str:
    return f"privy_deposit:{deposit_id}"


def _map_deposit_status(deposit) -> str:
    status = str(getattr(deposit, "status", "") or "").strip().lower()
    if status == PersonWalletDepositStatus.CONFIRMED.value:
        return IntentStatus.CONFIRMED.value
    if status in {"failed", "rejected"}:
        return IntentStatus.FAILED.value
    return IntentStatus.CREATED.value


def ensure_webapp_privy_deposit_intent(
    db: Session,
    deposit,
    *,
    webapp_initiated: bool = False,
    metadata_patch: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Intent PRIVY_DEPOSIT — uniquement si parcours webapp explicite (futur)."""
    if not webapp_initiated:
        logger.debug(
            "privy_deposit.intent_skipped_not_webapp_initiated",
            extra={"deposit_id": str(getattr(deposit, "id", ""))},
        )
        return None
    if deposit is None or not getattr(deposit, "person_id", None):
        return None

    try:
        meta: dict[str, Any] = {
            "deposit_status": getattr(deposit, "status", None),
            "transaction_kind": getattr(deposit, "transaction_kind", None),
            "asset": getattr(deposit, "asset", None),
            "amount": str(getattr(deposit, "amount", "")),
            "log_index": getattr(deposit, "log_index", None),
            "initiated_by": "webapp",
            **(metadata_patch or {}),
        }
        if getattr(deposit, "privy_webhook_event_id", None):
            meta["privy_webhook_event_id"] = str(deposit.privy_webhook_event_id)

        row, created = TransactionIntentRepository.upsert(
            db,
            person_id=deposit.person_id,
            product_type=PRIVY_DEPOSIT_PRODUCT,
            operation_type=IntentOperationType.DEPOSIT.value,
            idempotency_key=privy_deposit_intent_key(deposit.id),
            status=_map_deposit_status(deposit),
            wallet_address=getattr(deposit, "to_address", None),
            chain_id=getattr(deposit, "chain_id", None),
            tx_hash=getattr(deposit, "tx_hash", None),
            linked_table=PRIVY_DEPOSIT_LINKED_TABLE,
            linked_id=deposit.id,
            metadata_patch=meta,
        )
        db.flush()

        if row.tx_hash:
            try_link_raw_event_to_intent(db, row)

        if created:
            logger.info(
                "intent.privy_deposit.webapp_created",
                extra={"deposit_id": str(deposit.id), "intent_id": str(row.id)},
            )
        return {"intent_id": str(row.id), "created": created, "status": row.status}
    except Exception as exc:
        logger.warning(
            "intent.privy_deposit.webapp_sync_failed",
            extra={"deposit_id": str(getattr(deposit, "id", "")), "error": str(exc)},
            exc_info=True,
        )
        return None
