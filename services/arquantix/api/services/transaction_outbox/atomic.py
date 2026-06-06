"""Bundle atomique intent + swap + outbox (Phase 2 S1 — fondation, pas branché LI.FI runtime)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.enums import IntentOperationType, IntentProductType, IntentStatus
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)


@dataclass(frozen=True)
class IntentSwapOutboxBundle:
    intent: TransactionIntent
    swap: PersonWalletSwap
    outbox: TransactionOutbox


def persist_intent_swap_outbox_atomic(
    db: Session,
    *,
    person_id: UUID,
    from_asset: str,
    to_asset: str,
    from_chain: str,
    to_chain: str,
    amount_in: Decimal,
    correlation_id: UUID | None = None,
    swap_status: str = "PENDING",
    record_initial_transition: bool = True,
) -> IntentSwapOutboxBundle:
    """Crée intent orchestrateur + swap + outbox dans la session DB courante (une TX).

    Non branché au runtime LI.FI en S1 — utilisé par les tests d'atomicité et S2+.
    """
    correlation = correlation_id or uuid4()

    swap = PersonWalletSwap(
        person_id=person_id,
        status=swap_status,
        from_asset=from_asset,
        to_asset=to_asset,
        from_chain=from_chain,
        to_chain=to_chain,
        amount_in=amount_in,
        audit_log=[],
    )
    db.add(swap)
    db.flush()

    idempotency_key = f"lifi_swap:{swap.id}"
    intent = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.LIFI_SWAP.value,
        operation_type=IntentOperationType.SWAP.value,
        requested_action="swap",
        idempotency_key=idempotency_key,
        status=IntentStatus.CREATED.value,
        current_phase="CREATED",
        correlation_id=correlation,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
        assets_json={
            "from": {"asset": from_asset, "amount": str(amount_in)},
            "to": {"asset": to_asset},
        },
        metadata_json={"phase2_orchestrator": True, "s1_foundation": True},
    )
    db.add(intent)
    db.flush()

    outbox = TransactionOutboxRepository.insert_event(
        db,
        intent_id=intent.id,
        event_type=OutboxEventType.INTENT_CREATED.value,
        payload_json={"swap_id": str(swap.id), "person_id": str(person_id)},
        correlation_id=correlation,
    )

    if record_initial_transition:
        TransactionIntentTransitionRepository.insert_transition(
            db,
            intent_id=intent.id,
            from_status=None,
            to_status=IntentStatus.CREATED.value,
            phase="CREATED",
            actor="atomic_bootstrap",
            metadata_json={"swap_id": str(swap.id)},
        )

    return IntentSwapOutboxBundle(intent=intent, swap=swap, outbox=outbox)


def bundle_coherence_checks(bundle: IntentSwapOutboxBundle) -> dict[str, Any]:
    """Vérifie correlation_id, linked_id et idempotency_key."""
    intent, swap, outbox = bundle.intent, bundle.swap, bundle.outbox
    return {
        "linked_id_matches_swap": intent.linked_id == swap.id,
        "linked_table": intent.linked_table == "person_wallet_swaps",
        "idempotency_key": intent.idempotency_key == f"lifi_swap:{swap.id}",
        "outbox_correlation_matches_intent": outbox.correlation_id == intent.correlation_id,
        "outbox_intent_matches": outbox.intent_id == intent.id,
        "outbox_payload_swap_id": (outbox.payload_json or {}).get("swap_id") == str(swap.id),
    }
