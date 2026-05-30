"""Synchronisation transaction_intents ↔ Morpho Earn (Phase 7B — observabilité)."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from .enums import IntentOperationType, IntentProductType, IntentStatus
from .raw_event_link import try_link_raw_event_to_intent
from .repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

MORPHO_LINKED_TABLE = "onchain_vault_transactions"
MORPHO_PRODUCT = IntentProductType.MORPHO_EARN.value

MORPHO_EARN_OPERATIONS = frozenset({"deposit", "withdraw"})
MORPHO_VAULT_APPROVE_OPERATIONS = frozenset({"approve", "authorize"})
MORPHO_DIRECT_INTEGRATION = "direct_morpho"


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
                "vault_operation": mapped_op,
                **(extra_metadata or {}),
            },
        )
        db.flush()

        if tx_hash:
            try_link_raw_event_to_intent(db, row)

        _dual_write_morpho_attempt(
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
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        vault_status = None
        if status == IntentStatus.CONFIRMED.value:
            vault_status = "success"
        elif status == IntentStatus.FAILED.value:
            vault_status = "failed"
        _dual_write_morpho_attempt(
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
            "intent.morpho.status_update_failed",
            extra={"vault_transaction_id": vault_transaction_id, "error": str(exc)},
        )
        return None


def _dual_write_morpho_attempt(
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
        integration_mode="direct_morpho",
        tx_hash=tx_hash,
        vault_status=status,
        intent_id=resolve_intent_id_for_vault_transaction(
            db,
            person_id=person_id,
            vault_transaction_id=vault_transaction_id,
        ),
    )


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


def _load_morpho_vault_transaction(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
) -> dict[str, Any] | None:
    row = db.execute(
        sa.text(
            """
            SELECT id, person_id, operation, status, tx_hash, chain_id, wallet_address,
                   idempotency_key, group_key, integration_mode, tx_index, asset_symbol, amount_raw
            FROM onchain_vault_transactions
            WHERE id = :id AND person_id = :person_id
            """
        ),
        {"id": vault_transaction_id, "person_id": str(person_id)},
    ).mappings().first()
    return dict(row) if row else None


def sync_morpho_vault_approve_attempt(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    tx_hash: str | None = None,
    vault_status: str | None = None,
) -> dict[str, Any] | None:
    """
    Dual-write forward pour OVT Morpho approve/authorize — sans transaction_intent.

    Ne lève pas — retourne None si OVT hors périmètre (deposit, withdraw, autre intégration).
    """
    row = _load_morpho_vault_transaction(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
    )
    if row is None:
        return None

    integration_mode = str(row.get("integration_mode") or "").strip().lower()
    operation = str(row.get("operation") or "").strip().lower()
    if integration_mode != MORPHO_DIRECT_INTEGRATION or operation not in MORPHO_VAULT_APPROVE_OPERATIONS:
        return None

    resolved_tx = (tx_hash or row.get("tx_hash") or "").strip().lower() or None
    resolved_status = (vault_status or row.get("status") or "").strip().lower()
    if resolved_status == "success" and not resolved_tx:
        return None

    group_key = str(row.get("group_key") or row.get("idempotency_key") or vault_transaction_id)
    step_index = int(row.get("tx_index") or 0)
    chain_id = int(row.get("chain_id") or 8453)
    wallet_address = str(row.get("wallet_address") or "")

    from services.transaction_attempts.dual_write import dual_write_vault_step
    from services.transaction_attempts.enums import AttemptStepType
    from services.transaction_attempts.models import OnchainTransactionAttempt
    from services.transaction_attempts.repository import OnchainTransactionAttemptRepository

    step_type = (
        AttemptStepType.APPROVE.value
        if operation == "approve"
        else AttemptStepType.AUTHORIZE.value
    )

    existing_ref = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.linked_reference_id == vault_transaction_id,
            OnchainTransactionAttempt.step_type == step_type,
        )
        .first()
    )
    if existing_ref is not None:
        return {
            "attempt_id": str(existing_ref.id),
            "intent_id": None,
            "vault_operation": operation,
            "already_exists": True,
        }

    dual_write_vault_step(
        db,
        person_id=person_id,
        vault_transaction_id=vault_transaction_id,
        chain_id=chain_id,
        wallet_address=wallet_address,
        operation=operation,
        group_key=group_key,
        step_index=step_index,
        integration_mode=MORPHO_DIRECT_INTEGRATION,
        tx_hash=resolved_tx,
        vault_status=resolved_status,
        intent_id=None,
        asset_symbol=str(row.get("asset_symbol") or "") or None,
        amount_raw=str(row.get("amount_raw") or "") if row.get("amount_raw") is not None else None,
        dual_write_source="morpho_vault_approve_sync",
    )

    idem = f"morpho:{person_id}:{group_key}:{step_type}:{step_index}"
    attempt = OnchainTransactionAttemptRepository.find_by_composite_key(
        db,
        idempotency_key=idem,
        step_type=step_type,
    )
    if attempt is None:
        return None

    return {
        "attempt_id": str(attempt.id),
        "intent_id": None,
        "vault_operation": operation,
        "status": attempt.status,
        "tx_hash": attempt.tx_hash,
        "linked_reference_id": vault_transaction_id,
        "group_key": group_key,
    }
