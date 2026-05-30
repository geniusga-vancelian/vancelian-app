"""Persistence append-only transaction_trace_events — best-effort."""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session


class TransactionTraceRepository:

    @staticmethod
    def append(db: Session, *, trace_id: UUID, payload: dict[str, Any]) -> None:
        """Insert append-only sans ORM (évite les dépendances mapper dans les scripts)."""
        metadata = payload.get("metadata_json")
        db.execute(
            sa.text(
                """
                INSERT INTO transaction_trace_events (
                    id, event_type, person_id, intent_id, attempt_id,
                    group_key, idempotency_key, protocol, operation_type, step_type,
                    status_from, status_to, tx_hash, chain_id,
                    linked_table, linked_id, linked_reference_id,
                    source, message, metadata_json
                ) VALUES (
                    :id, :event_type, :person_id, :intent_id, :attempt_id,
                    :group_key, :idempotency_key, :protocol, :operation_type, :step_type,
                    :status_from, :status_to, :tx_hash, :chain_id,
                    :linked_table, :linked_id, :linked_reference_id,
                    :source, :message, CAST(:metadata_json AS jsonb)
                )
                """
            ),
            {
                "id": str(trace_id),
                "event_type": str(payload.get("event_type") or ""),
                "person_id": _uuid_str_or_none(payload.get("person_id")),
                "intent_id": _uuid_str_or_none(payload.get("intent_id")),
                "attempt_id": _uuid_str_or_none(payload.get("attempt_id")),
                "group_key": payload.get("group_key"),
                "idempotency_key": payload.get("idempotency_key"),
                "protocol": payload.get("protocol"),
                "operation_type": payload.get("operation_type"),
                "step_type": payload.get("step_type"),
                "status_from": payload.get("status_from"),
                "status_to": payload.get("status_to"),
                "tx_hash": payload.get("tx_hash"),
                "chain_id": payload.get("chain_id"),
                "linked_table": payload.get("linked_table"),
                "linked_id": _uuid_str_or_none(payload.get("linked_id")),
                "linked_reference_id": payload.get("linked_reference_id"),
                "source": payload.get("source"),
                "message": payload.get("message"),
                "metadata_json": json.dumps(metadata) if metadata is not None else None,
            },
        )
        db.flush()


def _uuid_str_or_none(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return str(value)
    return str(value)
