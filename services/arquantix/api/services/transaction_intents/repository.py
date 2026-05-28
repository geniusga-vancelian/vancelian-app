"""Repository transaction_intents — upsert idempotent."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent

from .enums import IntentStatus


def intent_to_dict(row: TransactionIntent) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "person_id": str(row.person_id) if row.person_id else None,
        "wallet_address": row.wallet_address,
        "chain_id": row.chain_id,
        "product_type": row.product_type,
        "operation_type": row.operation_type,
        "idempotency_key": row.idempotency_key,
        "status": row.status,
        "tx_hash": row.tx_hash,
        "raw_onchain_event_id": (
            str(row.raw_onchain_event_id) if row.raw_onchain_event_id else None
        ),
        "linked_table": row.linked_table,
        "linked_id": str(row.linked_id) if row.linked_id else None,
        "linked_reference_id": getattr(row, "linked_reference_id", None),
        "metadata_json": row.metadata_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class TransactionIntentRepository:

    @staticmethod
    def find_by_composite_key(
        db: Session,
        *,
        person_id: UUID,
        product_type: str,
        operation_type: str,
        idempotency_key: str,
    ) -> TransactionIntent | None:
        return (
            db.query(TransactionIntent)
            .filter(
                TransactionIntent.person_id == person_id,
                TransactionIntent.product_type == product_type,
                TransactionIntent.operation_type == operation_type,
                TransactionIntent.idempotency_key == idempotency_key,
            )
            .first()
        )

    @staticmethod
    def find_by_linked(
        db: Session,
        *,
        linked_table: str,
        linked_id: UUID,
    ) -> TransactionIntent | None:
        return (
            db.query(TransactionIntent)
            .filter(
                TransactionIntent.linked_table == linked_table,
                TransactionIntent.linked_id == linked_id,
            )
            .order_by(TransactionIntent.created_at.desc())
            .first()
        )

    @staticmethod
    def find_by_lombard_group(
        db: Session,
        *,
        person_id: UUID,
        group_key: str,
        market_or_vault: str | None = None,
    ) -> TransactionIntent | None:
        from .lombard_intent_sync import (
            LOMBARD_LINKED_TABLE,
            LOMBARD_OPERATION,
            LOMBARD_PRODUCT,
            lombard_parent_intent_key,
        )

        key = lombard_parent_intent_key(
            person_id=person_id,
            market_or_vault=market_or_vault or "",
            idempotency_key=group_key,
        )
        row = TransactionIntentRepository.find_by_composite_key(
            db,
            person_id=person_id,
            product_type=LOMBARD_PRODUCT,
            operation_type=LOMBARD_OPERATION,
            idempotency_key=key,
        )
        if row is not None:
            return row
        return (
            db.query(TransactionIntent)
            .filter(
                TransactionIntent.person_id == person_id,
                TransactionIntent.product_type == LOMBARD_PRODUCT,
                TransactionIntent.linked_table == LOMBARD_LINKED_TABLE,
                TransactionIntent.linked_reference_id == group_key,
            )
            .order_by(TransactionIntent.created_at.desc())
            .first()
        )

    @staticmethod
    def find_by_bundle_batch(
        db: Session,
        *,
        person_id: UUID,
        bundle_id: str,
        batch_id: str,
    ) -> TransactionIntent | None:
        from .bundle_intent_sync import (
            BUNDLE_LINKED_TABLE,
            BUNDLE_OPERATION,
            BUNDLE_PRODUCT,
            bundle_parent_intent_key,
        )

        key = bundle_parent_intent_key(
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=batch_id,
        )
        row = TransactionIntentRepository.find_by_composite_key(
            db,
            person_id=person_id,
            product_type=BUNDLE_PRODUCT,
            operation_type=BUNDLE_OPERATION,
            idempotency_key=key,
        )
        if row is not None:
            return row
        return (
            db.query(TransactionIntent)
            .filter(
                TransactionIntent.person_id == person_id,
                TransactionIntent.product_type == BUNDLE_PRODUCT,
                TransactionIntent.linked_table == BUNDLE_LINKED_TABLE,
                TransactionIntent.linked_reference_id == batch_id,
            )
            .order_by(TransactionIntent.created_at.desc())
            .first()
        )

    @staticmethod
    def find_by_vault_transaction(
        db: Session,
        *,
        vault_transaction_id: str,
        person_id: UUID | None = None,
    ) -> TransactionIntent | None:
        q = db.query(TransactionIntent).filter(
            TransactionIntent.linked_table == "onchain_vault_transactions",
            TransactionIntent.linked_reference_id == vault_transaction_id,
        )
        if person_id is not None:
            q = q.filter(TransactionIntent.person_id == person_id)
        return q.order_by(TransactionIntent.created_at.desc()).first()

    @staticmethod
    def upsert(
        db: Session,
        *,
        person_id: UUID,
        product_type: str,
        operation_type: str,
        idempotency_key: str,
        status: str,
        wallet_address: str | None = None,
        chain_id: int | None = None,
        tx_hash: str | None = None,
        raw_onchain_event_id: UUID | None = None,
        linked_table: str | None = None,
        linked_id: UUID | None = None,
        linked_reference_id: str | None = None,
        metadata_patch: dict[str, Any] | None = None,
    ) -> tuple[TransactionIntent, bool]:
        row = TransactionIntentRepository.find_by_composite_key(
            db,
            person_id=person_id,
            product_type=product_type,
            operation_type=operation_type,
            idempotency_key=idempotency_key,
        )
        created = row is None
        if row is None:
            row = TransactionIntent(
                person_id=person_id,
                product_type=product_type,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
                status=status,
            )
            db.add(row)

        row.status = status
        if wallet_address is not None:
            row.wallet_address = wallet_address.strip().lower()
        if chain_id is not None:
            row.chain_id = chain_id
        if tx_hash is not None:
            row.tx_hash = tx_hash.strip().lower()
        if raw_onchain_event_id is not None:
            row.raw_onchain_event_id = raw_onchain_event_id
        if linked_table is not None:
            row.linked_table = linked_table
        if linked_id is not None:
            row.linked_id = linked_id
        if linked_reference_id is not None:
            row.linked_reference_id = linked_reference_id

        if metadata_patch:
            base = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            row.metadata_json = {**base, **metadata_patch}

        row.updated_at = datetime.now(timezone.utc)
        db.flush()
        return row, created

    @staticmethod
    def list_filtered(
        db: Session,
        *,
        person_id: UUID | None = None,
        wallet_address: str | None = None,
        product_type: str | None = None,
        status: str | None = None,
        tx_hash: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TransactionIntent], int]:
        q = db.query(TransactionIntent)
        if person_id is not None:
            q = q.filter(TransactionIntent.person_id == person_id)
        if wallet_address:
            q = q.filter(TransactionIntent.wallet_address == wallet_address.strip().lower())
        if product_type:
            q = q.filter(TransactionIntent.product_type == product_type.strip().lower())
        if status:
            q = q.filter(TransactionIntent.status == status.strip().lower())
        if tx_hash:
            q = q.filter(TransactionIntent.tx_hash == tx_hash.strip().lower())
        if created_from is not None:
            q = q.filter(TransactionIntent.created_at >= created_from)
        if created_to is not None:
            q = q.filter(TransactionIntent.created_at <= created_to)

        total = q.count()
        rows = (
            q.order_by(TransactionIntent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total
