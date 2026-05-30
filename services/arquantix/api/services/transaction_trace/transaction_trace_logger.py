"""
Transaction trace logging — observabilité humaine / ops (pas source of truth).

Émet :
- log applicatif JSON structuré (logger ``arquantix.transaction_trace``)
- persistance DB append-only best-effort si table ``transaction_trace_events`` présente
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session

from .enums import TraceEventType
from .repository import TransactionTraceRepository

logger = logging.getLogger("arquantix.transaction_trace")

_SENSITIVE_KEY_RE = re.compile(
    r"(password|secret|token|jwt|authorization|private_key|signature|api_key|mnemonic|seed)",
    re.I,
)
_REDACTED = "[REDACTED]"


def migration_172_ready(db: Session | None = None) -> bool:
    try:
        if db is not None:
            r = db.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_trace_events'"
                )
            )
            return r.fetchone() is not None
        from database import engine

        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_trace_events'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


def _sanitize_value(key: str, value: Any) -> Any:
    if _SENSITIVE_KEY_RE.search(key or ""):
        return _REDACTED
    if isinstance(value, dict):
        return _sanitize_metadata(value)
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value[:50]]
    if isinstance(value, str) and len(value) > 2000:
        return value[:2000] + "…"
    return value


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        clean[key] = _sanitize_value(str(key), value)
    return clean


def _norm_optional_uuid(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def log_transaction_trace(
    event_type: TraceEventType | str,
    *,
    db: Session | None = None,
    trace_id: UUID | None = None,
    person_id: UUID | str | None = None,
    intent_id: UUID | str | None = None,
    attempt_id: UUID | str | None = None,
    group_key: str | None = None,
    idempotency_key: str | None = None,
    protocol: str | None = None,
    operation_type: str | None = None,
    step_type: str | None = None,
    status_from: str | None = None,
    status_to: str | None = None,
    tx_hash: str | None = None,
    chain_id: int | None = None,
    linked_table: str | None = None,
    linked_id: UUID | str | None = None,
    linked_reference_id: str | None = None,
    source: str | None = None,
    message: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    persist_db: bool = True,
) -> dict[str, Any]:
    """
    Émet un événement trace structuré. Ne lève pas — best-effort uniquement.
    """
    trace_uuid = trace_id or uuid4()
    event_norm = (
        event_type.value if isinstance(event_type, TraceEventType) else str(event_type)
    )
    payload: dict[str, Any] = {
        "trace_id": str(trace_uuid),
        "event_type": event_norm,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "person_id": _norm_optional_uuid(person_id),
        "intent_id": _norm_optional_uuid(intent_id),
        "attempt_id": _norm_optional_uuid(attempt_id),
        "group_key": group_key,
        "idempotency_key": idempotency_key,
        "protocol": protocol,
        "operation_type": operation_type,
        "step_type": step_type,
        "status_from": status_from,
        "status_to": status_to,
        "tx_hash": tx_hash.strip().lower() if tx_hash else None,
        "chain_id": chain_id,
        "linked_table": linked_table,
        "linked_id": _norm_optional_uuid(linked_id),
        "linked_reference_id": linked_reference_id,
        "source": source,
        "message": message,
        "metadata_json": _sanitize_metadata(metadata_json),
    }

    try:
        logger.info(json.dumps(payload, default=str, ensure_ascii=False))
    except Exception:
        logger.info("transaction_trace.emit_failed", extra={"event_type": event_norm})

    if db is not None and persist_db and migration_172_ready(db):
        try:
            TransactionTraceRepository.append(db, trace_id=trace_uuid, payload=payload)
        except Exception as exc:
            logger.warning(
                "transaction_trace.db_persist_failed",
                extra={"event_type": event_norm, "error": str(exc)},
            )

    return payload


def log_attempt_transition_trace(
    db: Session | None,
    *,
    row: Any,
    status_from: str | None,
    status_to: str,
    source: str,
    transition: Any | None = None,
) -> None:
    event_map = {
        "signed": TraceEventType.ATTEMPT_SIGNED,
        "submitted": TraceEventType.ATTEMPT_SUBMITTED,
        "confirmed": TraceEventType.ATTEMPT_CONFIRMED,
        "failed": TraceEventType.ATTEMPT_FAILED,
        "reverted": TraceEventType.ATTEMPT_FAILED,
    }
    event = event_map.get(status_to, TraceEventType.ATTEMPT_SUBMITTED)
    meta: dict[str, Any] = {}
    if transition is not None:
        if getattr(transition, "error_code", None):
            meta["error_code"] = transition.error_code
        if getattr(transition, "error_message", None):
            meta["error_message"] = str(transition.error_message)[:500]

    log_transaction_trace(
        event,
        db=db,
        person_id=getattr(row, "person_id", None),
        intent_id=getattr(row, "intent_id", None),
        attempt_id=getattr(row, "id", None),
        group_key=getattr(row, "group_key", None),
        idempotency_key=getattr(row, "idempotency_key", None),
        protocol=getattr(row, "protocol", None),
        operation_type=getattr(row, "operation_type", None),
        step_type=getattr(row, "step_type", None),
        status_from=status_from,
        status_to=status_to,
        tx_hash=getattr(row, "tx_hash", None),
        chain_id=getattr(row, "chain_id", None),
        linked_table=getattr(row, "linked_table", None),
        linked_id=getattr(row, "linked_id", None),
        linked_reference_id=getattr(row, "linked_reference_id", None),
        source=source,
        message=f"attempt {status_from or '?'} -> {status_to}",
        metadata_json=meta or None,
    )
