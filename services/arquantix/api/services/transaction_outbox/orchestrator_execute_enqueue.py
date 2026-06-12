"""Auto-enqueue ``intent.execute`` — swap orchestrateur prêt à être signé/soumis côté serveur.

Complémentaire de ``orchestrator_settle_enqueue`` :
- ``intent.settle``  : swap déjà CONFIRMED (signé par le client) → comptabilité.
- ``intent.execute`` : swap quoté mais **pas encore signé** → le worker signe (Privy délégué) et soumet.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.lifi.orchestrator_allowlist import lifi_execution_worker_enabled_for_person
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import TransactionOutboxRepository

logger = logging.getLogger(__name__)

ENQUEUE_SOURCE = "auto_execute_enqueue"

# Swap signable côté serveur : quoté, pas encore soumis ni terminal.
EXECUTABLE_SWAP_STATES = frozenset(
    {SwapSessionStatus.QUOTE_RECEIVED.value, SwapSessionStatus.AWAITING_SIGNATURE.value}
)


@dataclass(frozen=True)
class OrchestratorExecuteEnqueueResult:
    enqueued: bool
    outbox: TransactionOutbox | None = None
    reason: str = ""


def _find_phase2_intent_for_swap(db: Session, swap) -> TransactionIntent | None:
    if swap is None or not getattr(swap, "id", None):
        return None
    intent = TransactionIntentRepository.find_by_linked(
        db, linked_table="person_wallet_swaps", linked_id=swap.id
    )
    if intent is None:
        return None
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    return intent if meta.get("phase2_orchestrator") else None


def maybe_enqueue_orchestrator_intent_execute(
    db: Session,
    swap,
) -> OrchestratorExecuteEnqueueResult:
    """Enqueue idempotent ``intent.execute`` si le swap est signable côté serveur."""
    if swap is None or not getattr(swap, "person_id", None):
        return OrchestratorExecuteEnqueueResult(False, reason="missing_swap_or_person")

    if not lifi_execution_worker_enabled_for_person(db, swap.person_id):
        return OrchestratorExecuteEnqueueResult(False, reason="execution_worker_not_enabled")

    swap_status = str(getattr(swap, "status", "") or "").upper()
    if swap_status not in EXECUTABLE_SWAP_STATES:
        return OrchestratorExecuteEnqueueResult(False, reason=f"swap_status:{swap_status or '?'}")

    intent = _find_phase2_intent_for_swap(db, swap)
    if intent is None:
        return OrchestratorExecuteEnqueueResult(False, reason="no_phase2_orchestrator_intent")

    outbox, created = TransactionOutboxRepository.insert_event_idempotent_per_intent_type(
        db,
        intent_id=intent.id,
        event_type=OutboxEventType.INTENT_EXECUTE.value,
        payload_json={
            "swap_id": str(swap.id),
            "person_id": str(swap.person_id),
            "source": ENQUEUE_SOURCE,
        },
        correlation_id=intent.correlation_id,
    )
    if not created:
        return OrchestratorExecuteEnqueueResult(
            False, outbox=outbox, reason="intent_execute_already_enqueued"
        )

    logger.info(
        "orchestrator_intent_execute_enqueued",
        extra={
            "swap_id": str(swap.id),
            "intent_id": str(intent.id),
            "outbox_id": str(outbox.id),
        },
    )
    return OrchestratorExecuteEnqueueResult(True, outbox=outbox, reason="enqueued")


def maybe_enqueue_orchestrator_intent_execute_after_worker_queued(
    db: Session,
    intent: TransactionIntent,
) -> OrchestratorExecuteEnqueueResult:
    """Après passage ``intent.created`` → QUEUED : enqueue l'exécution serveur si applicable."""
    if (intent.linked_table or "").strip() != "person_wallet_swaps" or not intent.linked_id:
        return OrchestratorExecuteEnqueueResult(False, reason="no_linked_swap")

    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    if not meta.get("phase2_orchestrator"):
        return OrchestratorExecuteEnqueueResult(False, reason="not_orchestrator_intent")

    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == intent.linked_id).first()
    if swap is None:
        return OrchestratorExecuteEnqueueResult(False, reason="linked_swap_not_found")

    return maybe_enqueue_orchestrator_intent_execute(db, swap)
