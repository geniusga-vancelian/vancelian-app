"""Worker outbox ``intent.execute`` — exécution serveur d'un swap (signature déléguée Privy).

Défile les événements ``intent.execute`` et appelle ``execute_prepared_swap_server_side``
(signature serveur + submit + settlement). Flag ``LIFI_EXECUTION_WORKER_ENABLED`` + allowlist.

Si la signature serveur n'est pas possible (wallet non délégué, non configuré…), la fonction
d'exécution retombe sur ``awaiting_signature`` : l'événement est marqué traité (le client
historique pourra toujours signer), pas d'échec dur.
"""
from __future__ import annotations

import logging
import os
import socket
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.config import lifi_execution_worker_enabled
from services.lifi.orchestrator_allowlist import lifi_execution_worker_enabled_for_person
from services.onchain_indexer.models import TransactionIntent
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)

logger = logging.getLogger(__name__)

WORKER_ACTOR = "outbox_worker_intent_execute"
_RETRY_DELAY_SECONDS = 30


def _worker_instance_id() -> str:
    return f"{socket.gethostname() or 'local'}:{os.getpid()}"


def _resolve_swap_and_person(
    db: Session, intent: TransactionIntent, outbox: TransactionOutbox
) -> tuple[UUID, UUID] | None:
    """swap_id + person_id depuis l'intent lié (fallback payload outbox)."""
    person_id = intent.person_id
    swap_id = intent.linked_id if (intent.linked_table or "") == "person_wallet_swaps" else None
    if swap_id is None:
        payload = outbox.payload_json if isinstance(outbox.payload_json, dict) else {}
        raw = payload.get("swap_id")
        if raw:
            try:
                swap_id = UUID(str(raw))
            except (ValueError, TypeError):
                swap_id = None
    if swap_id is None or person_id is None:
        return None
    return swap_id, person_id


def handle_intent_execute_event(
    db: Session,
    outbox: TransactionOutbox,
    *,
    execute_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Exécute le swap lié à l'intent côté serveur. Retourne un résumé (phase, signed)."""
    if execute_fn is None:
        from services.trade_core.server_execution import execute_prepared_swap_server_side

        execute_fn = execute_prepared_swap_server_side

    intent = db.query(TransactionIntent).filter(TransactionIntent.id == outbox.intent_id).one()
    resolved = _resolve_swap_and_person(db, intent, outbox)
    if resolved is None:
        return {"skipped": True, "reason": "swap_or_person_unresolved"}

    swap_id, person_id = resolved
    result = execute_fn(db, person_id=person_id, swap_id=swap_id)

    TransactionIntentTransitionRepository.insert_transition(
        db,
        intent_id=intent.id,
        from_status=intent.status,
        to_status=intent.status,
        phase="EXECUTED" if result.signed_server_side else "EXECUTE_DEFERRED",
        actor=WORKER_ACTOR,
        metadata_json={
            "outbox_id": str(outbox.id),
            "swap_id": str(swap_id),
            "result_phase": result.phase,
            "signed_server_side": result.signed_server_side,
            "fallback_reason": result.fallback_reason,
        },
    )
    return {
        "swap_id": str(swap_id),
        "phase": result.phase,
        "signed_server_side": result.signed_server_side,
        "fallback_reason": result.fallback_reason,
    }


def process_transaction_outbox_intent_execute(
    db: Session,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Poll ``intent.execute`` et exécute les swaps côté serveur. Flag ``LIFI_EXECUTION_WORKER_ENABLED``."""
    if not lifi_execution_worker_enabled():
        return {"enabled": False, "polled": 0, "processed": 0, "failed": 0, "skipped": True}

    locked_by = _worker_instance_id()
    events = TransactionOutboxRepository.poll_pending_events(
        db,
        event_type=OutboxEventType.INTENT_EXECUTE.value,
        limit=limit,
        locked_by=locked_by,
    )

    processed = 0
    failed = 0
    skipped_allowlist = 0
    signed = 0
    errors: list[dict[str, str]] = []

    for event in events:
        intent = db.query(TransactionIntent).filter(TransactionIntent.id == event.intent_id).first()
        if intent is None or not lifi_execution_worker_enabled_for_person(db, intent.person_id):
            TransactionOutboxRepository.release_processing_lock(db, event)
            skipped_allowlist += 1
            continue
        try:
            summary = handle_intent_execute_event(db, event)
            TransactionOutboxRepository.mark_processed(db, event)
            processed += 1
            if summary.get("signed_server_side"):
                signed += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "outbox_intent_execute_handler_failed",
                extra={"outbox_id": str(event.id), "intent_id": str(event.intent_id)},
                exc_info=True,
            )
            TransactionOutboxRepository.mark_failure(
                db, event, error=str(exc), retry_delay_seconds=_RETRY_DELAY_SECONDS
            )
            failed += 1
            errors.append({"outbox_id": str(event.id), "error": str(exc)})

    if processed or failed or skipped_allowlist:
        db.commit()

    return {
        "enabled": True,
        "polled": len(events),
        "processed": processed,
        "signed_server_side": signed,
        "failed": failed,
        "skipped_allowlist": skipped_allowlist,
        "errors": errors,
    }
