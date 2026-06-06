"""Repository transaction_outbox et transitions (Phase 2 S1)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

    @staticmethod
    def poll_pending_events(
        db: Session,
        *,
        event_type: str,
        limit: int,
        locked_by: str,
    ) -> list[TransactionOutbox]:
        """Poll outbox pending (S2b — ``FOR UPDATE SKIP LOCKED``)."""
        now = datetime.now(timezone.utc)
        q = (
            db.query(TransactionOutbox)
            .filter(
                TransactionOutbox.status == OutboxEventStatus.PENDING.value,
                TransactionOutbox.event_type == event_type,
                TransactionOutbox.next_retry_at <= now,
            )
            .order_by(TransactionOutbox.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = q.all()
        for row in rows:
            row.status = OutboxEventStatus.PROCESSING.value
            row.locked_by = locked_by
            row.locked_at = now
        if rows:
            db.flush()
        return rows

    @staticmethod
    def mark_processed(db: Session, row: TransactionOutbox) -> None:
        now = datetime.now(timezone.utc)
        row.status = OutboxEventStatus.PROCESSED.value
        row.processed_at = now
        row.locked_by = None
        row.locked_at = None
        row.last_error = None
        db.flush()

    @staticmethod
    def mark_failure(
        db: Session,
        row: TransactionOutbox,
        *,
        error: str,
        retry_delay_seconds: int = 30,
    ) -> None:
        now = datetime.now(timezone.utc)
        row.attempt_count = int(row.attempt_count or 0) + 1
        row.last_error = error[:2000] if error else None
        row.locked_by = None
        row.locked_at = None
        if row.attempt_count >= int(row.max_attempts or 10):
            row.status = OutboxEventStatus.DEAD_LETTER.value
        else:
            row.status = OutboxEventStatus.PENDING.value
            row.next_retry_at = now + timedelta(seconds=retry_delay_seconds)
        db.flush()


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
