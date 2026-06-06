"""Repository transaction_outbox et transitions (Phase 2 S1)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.transaction_outbox.enums import OutboxEventStatus
from services.transaction_outbox.models import TransactionIntentTransition, TransactionOutbox


class TransactionOutboxRepository:

    @staticmethod
    def insert_event(
        db: Session,
        *,
        intent_id: UUID,
        event_type: str,
        payload_json: dict[str, Any] | None = None,
        correlation_id: UUID | None = None,
        status: str = OutboxEventStatus.PENDING.value,
    ) -> TransactionOutbox:
        row = TransactionOutbox(
            intent_id=intent_id,
            event_type=event_type,
            payload_json=payload_json,
            correlation_id=correlation_id,
            status=status,
            next_retry_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def find_by_intent(
        db: Session,
        intent_id: UUID,
        *,
        event_type: str | None = None,
    ) -> list[TransactionOutbox]:
        q = db.query(TransactionOutbox).filter(TransactionOutbox.intent_id == intent_id)
        if event_type is not None:
            q = q.filter(TransactionOutbox.event_type == event_type)
        return q.order_by(TransactionOutbox.created_at.asc()).all()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(TransactionOutbox).count()


class TransactionIntentTransitionRepository:

    @staticmethod
    def insert_transition(
        db: Session,
        *,
        intent_id: UUID,
        to_status: str,
        from_status: str | None = None,
        phase: str | None = None,
        actor: str = "system",
        metadata_json: dict[str, Any] | None = None,
    ) -> TransactionIntentTransition:
        row = TransactionIntentTransition(
            intent_id=intent_id,
            from_status=from_status,
            to_status=to_status,
            phase=phase,
            actor=actor,
            metadata_json=metadata_json,
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def count_for_intent(db: Session, intent_id: UUID) -> int:
        return (
            db.query(TransactionIntentTransition)
            .filter(TransactionIntentTransition.intent_id == intent_id)
            .count()
        )
