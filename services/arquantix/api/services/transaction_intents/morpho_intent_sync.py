"""Synchronisation transaction_intents ↔ Morpho Earn (Phase 7B — observabilité)."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .enums import IntentOperationType, IntentProductType, IntentStatus
from .raw_event_link import try_link_raw_event_to_intent
from .repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

MORPHO_LINKED_TABLE = "onchain_vault_transactions"
MORPHO_PRODUCT = IntentProductType.MORPHO_EARN.value

MORPHO_EARN_OPERATIONS = frozenset({"deposit", "withdraw"})


def morpho_intent_key(
    *,
    person_id: UUID,
    vault_address: str,
    operation: str,
    idempotency_key: str,
    tx_index: int,
) -> str:
    return (
        f"morpho_earn:{person_id}:{vault_address.lower()}:{operation}:"
        f"{idempotency_key}:{tx_index}"
    )


def _map_operation(operation: str) -> str | None:
    op = (operation or "").strip().lower()
    if op not in MORPHO_EARN_OPERATIONS:
        return None
    return op


def ensure_morpho_intent_for_vault_transaction(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    vault_address: str,
    chain_id: int,
    wallet_address: str,
    operation: str,
    idempotency_key: str,
    tx_index: int,
    tx_hash: str | None = None,
    vault_status: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Crée ou met à jour un intent Morpho (awaiting_signature / submitted selon tx_hash).

    Ne lève pas — retourne None si opération hors périmètre (ex. approve).
    """
    mapped_op = _map_operation(operation)
    if mapped_op is None:
        return None

    try:
        status = IntentStatus.AWAITING_SIGNATURE.value
        if tx_hash:
            status = IntentStatus.SUBMITTED.value
        if vault_status == "pending" and not tx_hash:
            status = IntentStatus.AWAITING_SIGNATURE.value

        row, created = TransactionIntentRepository.upsert(
            db,
            person_id=person_id,
            product_type=MORPHO_PRODUCT,
            operation_type=mapped_op,
            idempotency_key=morpho_intent_key(
                person_id=person_id,
                vault_address=vault_address,
                operation=mapped_op,
                idempotency_key=idempotency_key,
                tx_index=tx_index,
            ),
            status=status,
            wallet_address=wallet_address,
            chain_id=chain_id,
            tx_hash=tx_hash,
            linked_table=MORPHO_LINKED_TABLE,
            linked_reference_id=vault_transaction_id,
            metadata_patch={
                "vault_transaction_id": vault_transaction_id,
                "vault_address": vault_address.lower(),
                "tx_index": tx_index,
                "group_idempotency_key": idempotency_key,
                **(extra_metadata or {}),
            },
        )
        db.flush()

        if tx_hash:
            try_link_raw_event_to_intent(db, row)

        return {
            "intent_id": str(row.id),
            "created": created,
            "status": row.status,
        }
    except Exception as exc:
        logger.warning(
            "intent.morpho.sync_failed",
            extra={
                "vault_transaction_id": vault_transaction_id,
                "operation": operation,
                "error": str(exc),
            },
            exc_info=True,
        )
        return None


def mark_morpho_intent_submitted(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    vault_address: str,
    operation: str,
    idempotency_key: str,
    tx_index: int,
    tx_hash: str,
    chain_id: int | None = None,
    wallet_address: str | None = None,
) -> dict[str, Any] | None:
    mapped_op = _map_operation(operation)
    if mapped_op is None:
        return None
    try:
        row = TransactionIntentRepository.find_by_composite_key(
            db,
            person_id=person_id,
            product_type=MORPHO_PRODUCT,
            operation_type=mapped_op,
            idempotency_key=morpho_intent_key(
                person_id=person_id,
                vault_address=vault_address,
                operation=mapped_op,
                idempotency_key=idempotency_key,
                tx_index=tx_index,
            ),
        )
        if row is None:
            return ensure_morpho_intent_for_vault_transaction(
                db,
                person_id=person_id,
                vault_transaction_id=vault_transaction_id,
                vault_address=vault_address,
                chain_id=chain_id or 8453,
                wallet_address=wallet_address or "",
                operation=operation,
                idempotency_key=idempotency_key,
                tx_index=tx_index,
                tx_hash=tx_hash,
            )

        row.status = IntentStatus.SUBMITTED.value
        row.tx_hash = tx_hash.strip().lower()
        row.linked_reference_id = vault_transaction_id
        db.add(row)
        db.flush()
        try_link_raw_event_to_intent(db, row)
        db.flush()
        return {"intent_id": str(row.id), "status": row.status}
    except Exception as exc:
        logger.warning("intent.morpho.submitted_failed", extra={"error": str(exc)})
        return None


def _update_morpho_intent_status(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    status: str,
    tx_hash: str | None = None,
) -> dict[str, Any] | None:
    try:
        row = TransactionIntentRepository.find_by_vault_transaction(
            db,
            vault_transaction_id=vault_transaction_id,
            person_id=person_id,
        )
        if row is None:
            return None

        row.status = status
        if tx_hash:
            row.tx_hash = tx_hash.strip().lower()
        db.add(row)
        db.flush()
        if tx_hash:
            try_link_raw_event_to_intent(db, row)
        return {"intent_id": str(row.id), "status": row.status}
    except Exception as exc:
        logger.warning(
            "intent.morpho.status_update_failed",
            extra={"vault_transaction_id": vault_transaction_id, "error": str(exc)},
        )
        return None


def mark_morpho_intent_confirmed(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    tx_hash: str | None = None,
) -> dict[str, Any] | None:
    return _update_morpho_intent_status(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
        status=IntentStatus.CONFIRMED.value,
        tx_hash=tx_hash,
    )


def mark_morpho_intent_failed(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    tx_hash: str | None = None,
    reason: str | None = None,
) -> dict[str, Any] | None:
    row = TransactionIntentRepository.find_by_vault_transaction(
        db,
        vault_transaction_id=vault_transaction_id,
        person_id=person_id,
    )
    if row is None:
        return None
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    row.metadata_json = {**meta, "failure_reason": reason} if reason else meta
    db.add(row)
    db.flush()
    return _update_morpho_intent_status(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
        status=IntentStatus.FAILED.value,
        tx_hash=tx_hash,
    )


def mark_morpho_intent_reconciliation_required(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    reason: str,
) -> dict[str, Any] | None:
    return _update_morpho_intent_status(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
        status=IntentStatus.RECONCILIATION_REQUIRED.value,
    )
