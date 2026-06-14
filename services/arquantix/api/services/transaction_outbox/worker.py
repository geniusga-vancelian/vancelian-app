"""Worker outbox Phase 2 S2b — handler ``intent.created`` uniquement.

Ne touche que ``transaction_intents``, ``transaction_intent_transitions``, ``transaction_outbox``.
Pas de settlement, controller, provider_submitted, ni table économique directe.
Product locks L4b : hook optionnel via ``TRANSACTION_PRODUCT_LOCKS_ENABLED`` (default OFF).
S4d : partition séquentielle par ``lock_key`` · reprise ``VALIDATED`` · retry lock conflict.
"""
from __future__ import annotations

import logging
import os
import socket
from typing import Any

from sqlalchemy.orm import Session

from services.lifi.config import lifi_outbox_worker_enabled
from services.lifi.orchestrator_allowlist import lifi_outbox_worker_enabled_for_person
from services.onchain_indexer.models import TransactionIntent
from services.product_locks.exceptions import ProductLockConflict409
from services.transaction_intents.enums import IntentStatus
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)
from services.transaction_outbox.worker_queue_hardening import partition_intent_created_events

logger = logging.getLogger(__name__)

WORKER_ACTOR = "outbox_worker_intent_created"
_RETRY_DELAY_SECONDS = 30
_LOCK_CONFLICT_RETRY_DELAY_SECONDS = 5


def _worker_instance_id() -> str:
    host = socket.gethostname() or "local"
    pid = os.getpid()
    return f"{host}:{pid}"


def _transition_validated(db: Session, intent: TransactionIntent, outbox: TransactionOutbox) -> None:
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


def _apply_locks_queue_and_enqueue_settle(
    db: Session,
    intent: TransactionIntent,
    outbox: TransactionOutbox,
) -> None:
    from services.transaction_outbox.orchestrator_execute_enqueue import (
        maybe_enqueue_orchestrator_intent_execute_after_worker_queued,
    )
    from services.transaction_outbox.orchestrator_product_locks import (
        apply_orchestrator_product_locks_before_queued,
    )
    from services.transaction_outbox.orchestrator_settle_enqueue import (
        maybe_enqueue_orchestrator_intent_settle_after_worker_queued,
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

    # Swap déjà CONFIRMED (signé client) → settle ; swap quoté non signé → execute serveur.
    settle = maybe_enqueue_orchestrator_intent_settle_after_worker_queued(db, intent)
    if not settle.enqueued:
        maybe_enqueue_orchestrator_intent_execute_after_worker_queued(db, intent)


def handle_intent_created_event(db: Session, outbox: TransactionOutbox) -> None:
    """CREATED → VALIDATED → QUEUED (phase uniquement — pas de gate balance S2b).

    S4d : reprise depuis ``VALIDATED`` si un lock conflict a interrompu le handler précédemment.
    """
    from services.transaction_outbox.orchestrator_product_locks import (
        release_orchestrator_product_locks_for_intent,
    )

    intent = db.query(TransactionIntent).filter(TransactionIntent.id == outbox.intent_id).one()

    # PR 1 — réconciliation read/repair-only : si le swap lié est déjà terminal, propager
    # son état à l'intent (empêche les intents orphelins en `created`/`queued`).
    from services.transaction_intents.orphan_intent_reconciliation import (
        reconcile_intent_from_linked_swap,
    )

    reconcile_intent_from_linked_swap(db, intent)

    if intent.status == IntentStatus.FAILED.value:
        release_orchestrator_product_locks_for_intent(
            db,
            intent,
            reason="intent_failed",
        )
        return

    phase = (intent.current_phase or IntentOrchestratorPhase.CREATED.value).upper()
    if phase == IntentOrchestratorPhase.QUEUED.value:
        return

    if phase == IntentOrchestratorPhase.VALIDATED.value:
        _apply_locks_queue_and_enqueue_settle(db, intent, outbox)
        return

    if phase != IntentOrchestratorPhase.CREATED.value:
        raise ValueError(f"intent_created_unexpected_phase:{phase}")

    _transition_validated(db, intent, outbox)
    _apply_locks_queue_and_enqueue_settle(db, intent, outbox)


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

    to_process, deferred_same_scope = partition_intent_created_events(db, events)
    for event in deferred_same_scope:
        TransactionOutboxRepository.release_processing_lock(db, event)

    processed = 0
    failed = 0
    requeued_lock_conflict = 0
    skipped_allowlist = 0
    errors: list[dict[str, str]] = []

    for event in to_process:
        intent = db.query(TransactionIntent).filter(TransactionIntent.id == event.intent_id).first()
        if intent is None or not lifi_outbox_worker_enabled_for_person(db, intent.person_id):
            TransactionOutboxRepository.release_processing_lock(db, event)
            skipped_allowlist += 1
            continue
        try:
            handle_intent_created_event(db, event)
            TransactionOutboxRepository.mark_processed(db, event)
            processed += 1
        except ProductLockConflict409 as exc:
            logger.info(
                "outbox_intent_created_lock_conflict_requeue",
                extra={"outbox_id": str(event.id), "intent_id": str(event.intent_id)},
            )
            TransactionOutboxRepository.mark_failure(
                db,
                event,
                error=str(exc),
                retry_delay_seconds=_LOCK_CONFLICT_RETRY_DELAY_SECONDS,
            )
            requeued_lock_conflict += 1
            errors.append({"outbox_id": str(event.id), "error": str(exc), "requeued": "lock_conflict"})
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
            if event.status == OutboxEventStatus.DEAD_LETTER.value and intent is not None:
                from services.transaction_outbox.orchestrator_product_locks import (
                    release_orchestrator_product_locks_for_intent,
                )

                release_orchestrator_product_locks_for_intent(
                    db,
                    intent,
                    reason="outbox_dead_letter",
                )
            failed += 1
            errors.append({"outbox_id": str(event.id), "error": str(exc)})

    if processed or failed or requeued_lock_conflict or skipped_allowlist or deferred_same_scope:
        db.commit()

    return {
        "enabled": True,
        "polled": len(events),
        "processed": processed,
        "failed": failed,
        "requeued_lock_conflict": requeued_lock_conflict,
        "deferred_same_scope": len(deferred_same_scope),
        "skipped_allowlist": skipped_allowlist,
        "errors": errors,
    }
