"""Repository onchain_transaction_attempts — upsert idempotent."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .models import OnchainTransactionAttempt


def attempt_to_dict(row: OnchainTransactionAttempt) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "person_id": str(row.person_id),
        "intent_id": str(row.intent_id) if row.intent_id else None,
        "parent_intent_id": str(row.parent_intent_id) if row.parent_intent_id else None,
        "chain_id": row.chain_id,
        "protocol": row.protocol,
        "operation_type": row.operation_type,
        "step_type": row.step_type,
        "step_index": row.step_index,
        "group_key": row.group_key,
        "idempotency_key": row.idempotency_key,
        "status": row.status,
        "tx_hash": row.tx_hash,
        "linked_table": row.linked_table,
        "linked_id": str(row.linked_id) if row.linked_id else None,
        "linked_reference_id": row.linked_reference_id,
        "metadata_json": row.metadata_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class OnchainTransactionAttemptRepository:

    @staticmethod
    def find_by_composite_key(
        db: Session,
        *,
        idempotency_key: str,
        step_type: str,
    ) -> OnchainTransactionAttempt | None:
        return (
            db.query(OnchainTransactionAttempt)
            .filter(
                OnchainTransactionAttempt.idempotency_key == idempotency_key,
                OnchainTransactionAttempt.step_type == step_type,
            )
            .first()
        )

    @staticmethod
    def find_by_linked(
        db: Session,
        *,
        linked_table: str,
        linked_id: UUID,
        step_type: str | None = None,
    ) -> OnchainTransactionAttempt | None:
        q = db.query(OnchainTransactionAttempt).filter(
            OnchainTransactionAttempt.linked_table == linked_table,
            OnchainTransactionAttempt.linked_id == linked_id,
        )
        if step_type:
            q = q.filter(OnchainTransactionAttempt.step_type == step_type)
        return q.order_by(OnchainTransactionAttempt.created_at.desc()).first()

    @staticmethod
    def list_by_group_key(
        db: Session,
        *,
        person_id: UUID,
        group_key: str,
    ) -> list[OnchainTransactionAttempt]:
        return (
            db.query(OnchainTransactionAttempt)
            .filter(
                OnchainTransactionAttempt.person_id == person_id,
                OnchainTransactionAttempt.group_key == group_key,
            )
            .order_by(OnchainTransactionAttempt.step_index.asc(), OnchainTransactionAttempt.created_at.asc())
            .all()
        )

    @staticmethod
    def upsert(
        db: Session,
        *,
        person_id: UUID,
        chain_id: int,
        protocol: str,
        operation_type: str,
        step_type: str,
        idempotency_key: str,
        status: str,
        step_index: int = 0,
        group_key: str | None = None,
        intent_id: UUID | None = None,
        parent_intent_id: UUID | None = None,
        person_crypto_wallet_id: UUID | None = None,
        wallet_address: str | None = None,
        tx_hash: str | None = None,
        asset_in: str | None = None,
        asset_out: str | None = None,
        amount_in: Any | None = None,
        amount_out_expected: Any | None = None,
        amount_out_actual: Any | None = None,
        linked_table: str | None = None,
        linked_id: UUID | None = None,
        linked_reference_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata_patch: dict[str, Any] | None = None,
        raw_request_json: dict[str, Any] | None = None,
        raw_submission_json: dict[str, Any] | None = None,
        raw_receipt_json: dict[str, Any] | None = None,
        raw_revert_json: dict[str, Any] | None = None,
    ) -> tuple[OnchainTransactionAttempt, bool]:
        row = OnchainTransactionAttemptRepository.find_by_composite_key(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
        )
        created = row is None
        if row is None:
            row = OnchainTransactionAttempt(
                person_id=person_id,
                chain_id=chain_id,
                protocol=protocol.strip().lower(),
                operation_type=operation_type.strip().lower(),
                step_type=step_type.strip().lower(),
                idempotency_key=idempotency_key,
                status=status,
            )
            db.add(row)

        row.status = status
        row.step_index = step_index
        if group_key is not None:
            row.group_key = group_key
        if intent_id is not None:
            row.intent_id = intent_id
        if parent_intent_id is not None:
            row.parent_intent_id = parent_intent_id
        if person_crypto_wallet_id is not None:
            row.person_crypto_wallet_id = person_crypto_wallet_id
        if wallet_address is not None:
            row.from_address = wallet_address.strip().lower()
        if tx_hash is not None:
            row.tx_hash = tx_hash.strip().lower()
        if asset_in is not None:
            row.asset_in = asset_in
        if asset_out is not None:
            row.asset_out = asset_out
        if amount_in is not None:
            row.amount_in = amount_in
        if amount_out_expected is not None:
            row.amount_out_expected = amount_out_expected
        if amount_out_actual is not None:
            row.amount_out_actual = amount_out_actual
        if linked_table is not None:
            row.linked_table = linked_table
        if linked_id is not None:
            row.linked_id = linked_id
        if linked_reference_id is not None:
            row.linked_reference_id = linked_reference_id
        if error_code is not None:
            row.error_code = error_code
        if error_message is not None:
            row.error_message = error_message
        if raw_request_json is not None:
            row.raw_request_json = raw_request_json
        if raw_submission_json is not None:
            row.raw_submission_json = raw_submission_json
        if raw_receipt_json is not None:
            row.raw_receipt_json = raw_receipt_json
        if raw_revert_json is not None:
            row.raw_revert_json = raw_revert_json
        if metadata_patch:
            base = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            row.metadata_json = {**base, **metadata_patch}

        row.updated_at = datetime.now(timezone.utc)
        db.flush()
        return row, created
