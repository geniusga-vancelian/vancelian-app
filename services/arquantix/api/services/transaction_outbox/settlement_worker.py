"""Worker outbox Phase 2 S3a/S3b — handler ``intent.settle`` → Settlement Layer.

S3a (flag ledger OFF) : metadata + phase uniquement.
S3b (flag ledger ON) : délègue projection ledger à ``settle`` (savepoint atomique).
Pas de PE, cost basis, provider, controller, ni ``COMPLETED``.
"""
from __future__ import annotations

import logging
import os
import socket
from typing import Any

from sqlalchemy.orm import Session

from services.lifi.config import lifi_outbox_worker_enabled
from services.lifi.orchestrator_allowlist import (
    lifi_outbox_worker_enabled_for_person,
    lifi_settlement_layer_ledger_enabled_for_person,
)
from services.onchain_indexer.models import TransactionIntent
from services.settlement.constants import SETTLEMENT_RECEIPT_METADATA_KEY
from services.settlement.preconditions import settlement_marker_present
from services.settlement.result import SettlementOutcome
from services.settlement.settle import settle_transaction_intent_idempotently
from services.transaction_intents.enums import IntentStatus
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)

logger = logging.getLogger(__name__)

WORKER_ACTOR = "outbox_worker_intent_settle"
_RETRY_DELAY_SECONDS = 30


class RetryableSettlementError(Exception):
    """Signal worker → retry outbox (ADR 002), sans transition terminale intent."""


def _worker_instance_id() -> str:
    host = socket.gethostname() or "local"
    pid = os.getpid()
    return f"{host}:{pid}"


def handle_intent_settle_event(db: Session, outbox: TransactionOutbox) -> None:
    """Appelle settlement skeleton et applique effets S3a (metadata + phase, pas d'écriture économique)."""
    result = settle_transaction_intent_idempotently(db, intent_id=outbox.intent_id)

    if result.outcome == SettlementOutcome.RETRYABLE_FAILURE:
        raise RetryableSettlementError(result.error_message or "settlement_retryable_failure")

    if result.outcome == SettlementOutcome.TERMINAL_FAILURE:
        intent = db.query(TransactionIntent).filter(TransactionIntent.id == outbox.intent_id).one()
        from_status = intent.status
        intent.status = IntentStatus.FAILED.value
        TransactionIntentTransitionRepository.insert_transition(
            db,
            intent_id=intent.id,
            from_status=from_status,
            to_status=IntentStatus.FAILED.value,
            phase=intent.current_phase,
            actor=WORKER_ACTOR,
            metadata_json={
                "outbox_id": str(outbox.id),
                "s3a": True,
                "error_code": result.error_code,
                "error_message": result.error_message,
            },
        )
        return

    if result.outcome == SettlementOutcome.NOOP_ALREADY_SETTLED:
        return

    if result.outcome != SettlementOutcome.SUCCESS:
        raise ValueError(f"unexpected_settlement_outcome:{result.outcome}")

    intent = db.query(TransactionIntent).filter(TransactionIntent.id == outbox.intent_id).one()
    receipt_hash = result.settlement_receipt_hash
    if not receipt_hash:
        raise ValueError("settlement_success_missing_receipt_hash")

    ledger_enabled = lifi_settlement_layer_ledger_enabled_for_person(db, intent.person_id)
    post_phase = (
        IntentOrchestratorPhase.LEDGER_SETTLED.value
        if ledger_enabled
        else IntentOrchestratorPhase.SETTLED_NOOP.value
    )

    if not settlement_marker_present(intent):
        meta = dict(intent.metadata_json) if isinstance(intent.metadata_json, dict) else {}
        meta[SETTLEMENT_RECEIPT_METADATA_KEY] = receipt_hash
        intent.metadata_json = meta

    TransactionIntentTransitionRepository.insert_transition(
        db,
        intent_id=intent.id,
        from_status=intent.status,
        to_status=intent.status,
        phase=post_phase,
        actor=WORKER_ACTOR,
        metadata_json={
            "outbox_id": str(outbox.id),
            "s3a": not ledger_enabled,
            "s3b": ledger_enabled,
            SETTLEMENT_RECEIPT_METADATA_KEY: receipt_hash,
        },
    )
    intent.current_phase = post_phase


def process_transaction_outbox_intent_settle(
    db: Session,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """Poll ``intent.settle`` et délègue au settlement skeleton. Flag ``LIFI_OUTBOX_WORKER_ENABLED`` requis."""
    if not lifi_outbox_worker_enabled():
        return {"enabled": False, "polled": 0, "processed": 0, "failed": 0, "skipped": True}

    locked_by = _worker_instance_id()
    events = TransactionOutboxRepository.poll_pending_events(
        db,
        event_type=OutboxEventType.INTENT_SETTLE.value,
        limit=limit,
        locked_by=locked_by,
    )

    processed = 0
    failed = 0
    retried = 0
    skipped_allowlist = 0
    errors: list[dict[str, str]] = []

    for event in events:
        intent = db.query(TransactionIntent).filter(TransactionIntent.id == event.intent_id).first()
        if intent is None or not lifi_outbox_worker_enabled_for_person(db, intent.person_id):
            TransactionOutboxRepository.release_processing_lock(db, event)
            skipped_allowlist += 1
            continue
        try:
            handle_intent_settle_event(db, event)
            TransactionOutboxRepository.mark_processed(db, event)
            processed += 1
        except RetryableSettlementError as exc:
            logger.info(
                "outbox_intent_settle_retryable",
                extra={"outbox_id": str(event.id), "intent_id": str(event.intent_id)},
            )
            TransactionOutboxRepository.mark_failure(
                db,
                event,
                error=str(exc),
                retry_delay_seconds=_RETRY_DELAY_SECONDS,
            )
            retried += 1
        except Exception as exc:
            logger.warning(
                "outbox_intent_settle_handler_failed",
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

    if processed or failed or retried or skipped_allowlist:
        db.commit()

    return {
        "enabled": True,
        "polled": len(events),
        "processed": processed,
        "failed": failed,
        "retried": retried,
        "skipped_allowlist": skipped_allowlist,
        "errors": errors,
    }
