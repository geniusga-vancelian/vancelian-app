"""Synchronisation transaction_intents ↔ Ledgity vault (Phase 1 — modèle Morpho)."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .enums import IntentOperationType, IntentProductType, IntentStatus
from .raw_event_link import try_link_raw_event_to_intent
from .repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

LEDGITY_LINKED_TABLE = "onchain_vault_transactions"
LEDGITY_PRODUCT = IntentProductType.LEDGITY_VAULT.value

LEDGITY_VAULT_OPERATIONS = frozenset({"deposit", "withdraw"})


def ledgity_intent_key(
    *,
    person_id: UUID,
    vault_address: str,
    operation: str,
    idempotency_key: str,
    tx_index: int,
) -> str:
    return (
        f"ledgity_vault:{person_id}:{vault_address.lower()}:{operation}:"
        f"{idempotency_key}:{tx_index}"
    )


def _map_operation(operation: str) -> str | None:
    op = (operation or "").strip().lower()
    if op not in LEDGITY_VAULT_OPERATIONS:
        return None
    return op


def ensure_ledgity_intent_for_vault_transaction(
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
            product_type=LEDGITY_PRODUCT,
            operation_type=mapped_op,
            idempotency_key=ledgity_intent_key(
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
            linked_table=LEDGITY_LINKED_TABLE,
            linked_reference_id=vault_transaction_id,
            metadata_patch={
                "vault_transaction_id": vault_transaction_id,
                "vault_address": vault_address.lower(),
                "tx_index": tx_index,
                "group_idempotency_key": idempotency_key,
                "integration_mode": "ledgity_vault",
                "vault_operation": mapped_op,
                **(extra_metadata or {}),
            },
        )
        db.flush()

        if tx_hash:
            try_link_raw_event_to_intent(db, row)

        _dual_write_ledgity_attempt(
            db,
            person_id=person_id,
            vault_transaction_id=vault_transaction_id,
            chain_id=chain_id,
            wallet_address=wallet_address,
            operation=mapped_op,
            group_key=idempotency_key,
            step_index=tx_index,
            tx_hash=tx_hash,
            vault_status=vault_status,
        )

        return {
            "intent_id": str(row.id),
            "created": created,
            "status": row.status,
        }
    except Exception as exc:
        logger.warning(
            "intent.ledgity.sync_failed",
            extra={
                "vault_transaction_id": vault_transaction_id,
                "operation": operation,
                "error": str(exc),
            },
            exc_info=True,
        )
        return None


def _update_ledgity_intent_status(
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
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        vault_status = None
        if status == IntentStatus.CONFIRMED.value:
            vault_status = "success"
        elif status == IntentStatus.FAILED.value:
            vault_status = "failed"
        _dual_write_ledgity_attempt(
            db,
            person_id=person_id,
            vault_transaction_id=vault_transaction_id,
            chain_id=row.chain_id or 8453,
            wallet_address=row.wallet_address or "",
            operation=str(meta.get("vault_operation") or row.operation_type or "deposit"),
            group_key=str(meta.get("group_idempotency_key") or vault_transaction_id),
            step_index=int(meta.get("tx_index") or 0),
            tx_hash=row.tx_hash,
            vault_status=vault_status,
        )
        return {"intent_id": str(row.id), "status": row.status}
    except Exception as exc:
        logger.warning(
            "intent.ledgity.status_update_failed",
            extra={"vault_transaction_id": vault_transaction_id, "error": str(exc)},
        )
        return None


def _dual_write_ledgity_attempt(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    chain_id: int,
    wallet_address: str,
    operation: str,
    group_key: str,
    step_index: int,
    tx_hash: str | None,
    vault_status: str | None,
) -> None:
    from services.transaction_attempts.dual_write import (
        dual_write_vault_step,
        resolve_intent_id_for_vault_transaction,
    )

    status = vault_status
    if status is None and tx_hash:
        status = "submitted"
    dual_write_vault_step(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
        chain_id=chain_id,
        wallet_address=wallet_address,
        operation=operation,
        group_key=group_key,
        step_index=step_index,
        integration_mode="ledgity_vault",
        tx_hash=tx_hash,
        vault_status=status,
        intent_id=resolve_intent_id_for_vault_transaction(
            db,
            person_id=person_id,
            vault_transaction_id=vault_transaction_id,
        ),
    )


def mark_ledgity_intent_confirmed(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    tx_hash: str | None = None,
) -> dict[str, Any] | None:
    return _update_ledgity_intent_status(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
        status=IntentStatus.CONFIRMED.value,
        tx_hash=tx_hash,
    )


def mark_ledgity_intent_failed(
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
    if reason:
        row.metadata_json = {**meta, "failure_reason": reason}
        db.add(row)
        db.flush()
    return _update_ledgity_intent_status(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
        status=IntentStatus.FAILED.value,
        tx_hash=tx_hash,
    )
