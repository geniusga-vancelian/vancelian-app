"""W3/W4 — auto-enqueue ``intent.settle`` quand swap orchestrateur standalone CONFIRMED."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.lifi.orchestrator_allowlist import lifi_intent_orchestrator_enabled_for_person
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.settlement.preconditions import settlement_marker_present
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import TransactionOutboxRepository

logger = logging.getLogger(__name__)

AUTO_ENQUEUE_READY_PHASES = frozenset(
    {
        IntentOrchestratorPhase.QUEUED.value,
        "ONCHAIN_CONFIRMED",
    }
)

SETTLED_PHASES = frozenset(
    {
        IntentOrchestratorPhase.SETTLED_NOOP.value,
        IntentOrchestratorPhase.LEDGER_SETTLED.value,
    }
)

ENQUEUE_SOURCE = "auto_confirm_enqueue"


@dataclass(frozen=True)
class OrchestratorSettleEnqueueResult:
    enqueued: bool
    outbox: TransactionOutbox | None = None
    reason: str = ""


def find_phase2_orchestrator_intent_for_swap(
    db: Session,
    swap: Any,
) -> TransactionIntent | None:
    """Intent orchestrateur lié au swap, ou ``None``."""
    if swap is None or not getattr(swap, "id", None):
        return None
    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
    )
    if intent is None:
        return None
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    if not meta.get("phase2_orchestrator"):
        return None
    return intent


def skip_legacy_swap_settlement_for_orchestrator(db: Session, swap: Any) -> bool:
    """Legacy ``apply_swap_settlement`` interdit si le rail orchestrateur est actif pour la personne.

    Ne skip pas sur un intent Phase 2 résiduel hors allowlist — évite un trou sans settlement.
    """
    intent = find_phase2_orchestrator_intent_for_swap(db, swap)
    if intent is None:
        return False
    person_id = getattr(swap, "person_id", None) or intent.person_id
    return lifi_intent_orchestrator_enabled_for_person(db, person_id)


def skip_legacy_cost_basis_for_orchestrator(db: Session, swap: Any) -> bool:
    """Ingest cost basis legacy interdit si le rail orchestrateur est actif pour la personne.

    Même règle que ``skip_legacy_swap_settlement_for_orchestrator`` : intent Phase 2 +
    allowlist + flag orchestrateur ON. Hors allowlist → legacy cost basis autorisé.
    """
    return skip_legacy_swap_settlement_for_orchestrator(db, swap)


def _validate_enqueue_preconditions(
    db: Session,
    swap: Any,
    intent: TransactionIntent,
) -> OrchestratorSettleEnqueueResult | None:
    """Retourne un résultat négatif si enqueue impossible, sinon ``None`` (OK)."""
    swap_status = str(getattr(swap, "status", "") or "").upper()
    if swap_status != SwapSessionStatus.CONFIRMED.value:
        return OrchestratorSettleEnqueueResult(False, reason=f"swap_status:{swap_status or '?'}")

    tx_hash = str(getattr(swap, "tx_hash", "") or "").strip()
    if not tx_hash:
        return OrchestratorSettleEnqueueResult(False, reason="missing_tx_hash")

    if is_bundle_internal_swap(swap):
        return OrchestratorSettleEnqueueResult(False, reason="bundle_internal_swap")

    if not lifi_intent_orchestrator_enabled_for_person(db, swap.person_id):
        return OrchestratorSettleEnqueueResult(False, reason="orchestrator_not_enabled")

    phase = (intent.current_phase or "").strip().upper()
    if phase in SETTLED_PHASES:
        return OrchestratorSettleEnqueueResult(False, reason=f"intent_phase_settled:{phase}")

    if settlement_marker_present(intent):
        return OrchestratorSettleEnqueueResult(False, reason="settlement_marker_present")

    if phase not in AUTO_ENQUEUE_READY_PHASES:
        return OrchestratorSettleEnqueueResult(
            False, reason=f"intent_phase_not_ready:{phase or '?'}"
        )

    return None


def maybe_enqueue_orchestrator_intent_settle(
    db: Session,
    swap: Any,
) -> OrchestratorSettleEnqueueResult:
    """Enqueue idempotent ``intent.settle`` — aucune écriture ledger / PE / cost basis."""
    if swap is None or not getattr(swap, "person_id", None):
        return OrchestratorSettleEnqueueResult(False, reason="missing_swap_or_person")

    intent = find_phase2_orchestrator_intent_for_swap(db, swap)
    if intent is None:
        return OrchestratorSettleEnqueueResult(False, reason="no_phase2_orchestrator_intent")

    blocked = _validate_enqueue_preconditions(db, swap, intent)
    if blocked is not None:
        return blocked

    outbox, created = TransactionOutboxRepository.insert_event_idempotent_per_intent_type(
        db,
        intent_id=intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
        payload_json={
            "swap_id": str(swap.id),
            "tx_hash": str(swap.tx_hash or "").strip(),
            "source": ENQUEUE_SOURCE,
        },
        correlation_id=intent.correlation_id,
    )
    if not created:
        return OrchestratorSettleEnqueueResult(
            False,
            outbox=outbox,
            reason="intent_settle_already_enqueued",
        )

    logger.info(
        "orchestrator_intent_settle_enqueued",
        extra={
            "swap_id": str(swap.id),
            "intent_id": str(intent.id),
            "outbox_id": str(outbox.id),
        },
    )
    return OrchestratorSettleEnqueueResult(True, outbox=outbox, reason="enqueued")


def maybe_enqueue_orchestrator_intent_settle_after_worker_queued(
    db: Session,
    intent: TransactionIntent,
) -> OrchestratorSettleEnqueueResult:
    """Rattrapage : swap déjà CONFIRMED avant passage worker ``intent.created`` → QUEUED."""
    if (intent.linked_table or "").strip() != "person_wallet_swaps" or not intent.linked_id:
        return OrchestratorSettleEnqueueResult(False, reason="no_linked_swap")

    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    if not meta.get("phase2_orchestrator"):
        return OrchestratorSettleEnqueueResult(False, reason="not_orchestrator_intent")

    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == intent.linked_id).first()
    if swap is None:
        return OrchestratorSettleEnqueueResult(False, reason="linked_swap_not_found")

    return maybe_enqueue_orchestrator_intent_settle(db, swap)
