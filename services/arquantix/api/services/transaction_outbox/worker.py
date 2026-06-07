"""Worker outbox Phase 2 S2b — handler ``intent.created`` uniquement.

Ne touche que ``transaction_intents``, ``transaction_intent_transitions``, ``transaction_outbox``.
Pas de settlement, controller, provider_submitted, ni table économique directe.
Product locks L4b : hook optionnel via ``TRANSACTION_PRODUCT_LOCKS_ENABLED`` (default OFF).
"""
from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from services.lifi.config import lifi_outbox_worker_enabled
from services.lifi.orchestrator_allowlist import lifi_outbox_worker_enabled_for_person
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.enums import IntentStatus
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)

logger = logging.getLogger(__name__)

WORKER_ACTOR = "outbox_worker_intent_created"
_RETRY_DELAY_SECONDS = 30


def _worker_instance_id() -> str:
    host = socket.gethostname() or "local"
    pid = os.getpid()
    return f"{host}:{pid}"


def handle_intent_created_event(db: Session, outbox: TransactionOutbox) -> None:
    """CREATED → VALIDATED → QUEUED (phase uniquement — pas de gate balance S2b)."""
    intent = db.query(TransactionIntent).filter(TransactionIntent.id == outbox.intent_id).one()

    if intent.status == IntentStatus.FAILED.value:
        return

    phase = (intent.current_phase or IntentOrchestratorPhase.CREATED.value).upper()
    if phase == IntentOrchestratorPhase.QUEUED.value:
        return
    if phase != IntentOrchestratorPhase.CREATED.value:
        raise ValueError(f"intent_created_unexpected_phase:{phase}")

    TransactionIntentTransitionRepository.insert_transition(
        db,
        intent_id=intent.id,
        from_status=intent.status,
        to_status=intent.status,
        phase=IntentOrchestratorPhase.VALIDATED.value,
        actor=WORKER_ACTOR,
        metadata_json={"outbox_id": str(outbox.id), "s2b": True},
    )
    intent.current_phase = IntentOrchestratorPhase.VALIDATED.value

    from services.transaction_outbox.orchestrator_product_locks import (
        apply_orchestrator_product_locks_before_queued,
    )

    apply_orchestrator_product_locks_before_queued(db, intent)

    TransactionIntentTransitionRepository.insert_transition(
        db,
        intent_id=intent.id,
        from_status=intent.status,
        to_status=intent.status,
        phase=IntentOrchestratorPhase.QUEUED.value,
        actor=WORKER_ACTOR,
        metadata_json={"outbox_id": str(outbox.id), "s2b": True},
    )
    intent.current_phase = IntentOrchestratorPhase.QUEUED.value

    from services.transaction_outbox.orchestrator_settle_enqueue import (
        maybe_enqueue_orchestrator_intent_settle_after_worker_queued,
    )

    maybe_enqueue_orchestrator_intent_settle_after_worker_queued(db, intent)


def process_transaction_outbox_intent_created(
    db: Session,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """Poll ``intent.created`` et applique transitions phase. Flag ``LIFI_OUTBOX_WORKER_ENABLED`` requis."""
    if not lifi_outbox_worker_enabled():
        return {"enabled": False, "polled": 0, "processed": 0, "failed": 0, "skipped": True}

    locked_by = _worker_instance_id()
    events = TransactionOutboxRepository.poll_pending_events(
        db,
        event_type=OutboxEventType.INTENT_CREATED.value,
        limit=limit,
        locked_by=locked_by,
    )

    processed = 0
    failed = 0
    skipped_allowlist = 0
    errors: list[dict[str, str]] = []

    for event in events:
        intent = db.query(TransactionIntent).filter(TransactionIntent.id == event.intent_id).first()
        if intent is None or not lifi_outbox_worker_enabled_for_person(db, intent.person_id):
            TransactionOutboxRepository.release_processing_lock(db, event)
            skipped_allowlist += 1
            continue
        try:
            handle_intent_created_event(db, event)
            TransactionOutboxRepository.mark_processed(db, event)
            processed += 1
        except Exception as exc:
            logger.warning(
                "outbox_intent_created_handler_failed",
                extra={"outbox_id": str(event.id), "intent_id": str(event.intent_id)},
                exc_info=True,
            )
            TransactionOutboxRepository.mark_failure(
                db,
                event,
                error=str(exc),
                retry_delay_seconds=_RETRY_DELAY_SECONDS,
            )
            failed += 1
            errors.append({"outbox_id": str(event.id), "error": str(exc)})

    if processed or failed or skipped_allowlist:
        db.commit()

    return {
        "enabled": True,
        "polled": len(events),
        "processed": processed,
        "failed": failed,
        "skipped_allowlist": skipped_allowlist,
        "errors": errors,
    }
