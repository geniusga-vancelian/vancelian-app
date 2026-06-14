"""PR4 — état de file d'un swap pour le front (mode autoritaire / enqueue-and-wait).

Traduit l'état réel backend (statut swap + slot global user) en une étape lisible par
l'UI. Lecture seule, aucun effet de bord.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus

# Valeurs exposées au front (alignées sur le stepper autoritaire PR4).
QUEUE_STATE_WAITING = "waiting_for_previous"
QUEUE_STATE_PREPARING = "preparing"
QUEUE_STATE_EXECUTING = "executing"
QUEUE_STATE_CONFIRMING = "confirming"
QUEUE_STATE_COMPLETED = "completed"
QUEUE_STATE_FAILED = "failed"

_PRE_EXECUTION_STATUSES = frozenset(
    {
        SwapSessionStatus.PENDING.value,
        SwapSessionStatus.QUOTE_RECEIVED.value,
        SwapSessionStatus.AWAITING_SIGNATURE.value,
    }
)


def compute_swap_queue_state(db: Session, swap, *, person_id: UUID) -> str:
    """Mappe le statut swap (+ slot global) vers une étape de file lisible par le front.

    - terminal → completed / failed
    - SUBMITTED → confirming (attente du receipt on-chain)
    - BROADCASTING → executing (signature serveur diffusée)
    - pré-exécution (PENDING/QUOTE_RECEIVED/AWAITING_SIGNATURE) :
        * un autre intent détient le slot user → waiting_for_previous (en file)
        * sinon → preparing (le worker va / est en train de préparer)
    """
    status = str(getattr(swap, "status", "") or "").upper()
    if status == SwapSessionStatus.CONFIRMED.value:
        return QUEUE_STATE_COMPLETED
    if status in {SwapSessionStatus.FAILED.value, SwapSessionStatus.EXPIRED.value}:
        return QUEUE_STATE_FAILED
    if status == SwapSessionStatus.SUBMITTED.value:
        return QUEUE_STATE_CONFIRMING
    if status == SwapSessionStatus.BROADCASTING.value:
        return QUEUE_STATE_EXECUTING

    if status in _PRE_EXECUTION_STATUSES:
        from services.product_locks.global_user_transaction_lock import (
            find_active_global_user_transaction_lock,
        )
        from services.transaction_intents.repository import TransactionIntentRepository

        lock = find_active_global_user_transaction_lock(db, person_id=person_id)
        if lock is not None:
            intent = TransactionIntentRepository.find_by_linked(
                db,
                linked_table="person_wallet_swaps",
                linked_id=swap.id,
            )
            if intent is None or lock.intent_id != intent.id:
                return QUEUE_STATE_WAITING
        return QUEUE_STATE_PREPARING

    return QUEUE_STATE_PREPARING
