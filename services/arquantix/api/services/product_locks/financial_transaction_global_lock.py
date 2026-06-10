"""File transactionnelle globale user — swap LI.FI · bundle dépôt · bundle rebalance.

Un seul slot actif par ``person_id`` (``GLOBAL_USER_TRANSACTION_LOCK_ENABLED``).
Tous les produits financiers passent par ce module — pas de lock parallèle par chemin.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.product_locks.exceptions import ProductLockConflict, TransactionInProgress409
from services.product_locks.global_user_transaction_lock import (
    AcquireGlobalUserTransactionLockResult,
    ReleaseGlobalUserTransactionLockResult,
    acquire_global_user_transaction_lock,
    release_global_user_transaction_lock,
    transaction_in_progress_409_from_conflict,
)
from services.product_locks.global_user_transaction_lock_config import (
    global_user_transaction_lock_enabled,
)

FINANCIAL_TRANSACTION_GLOBAL_LOCK_REASON = "financial_transaction"

_SWAP_TERMINAL_STATUSES = frozenset({"CONFIRMED", "FAILED", "EXPIRED"})

_V3_TERMINAL_STATUSES = frozenset({
    "COMPLETED",
    "COMPLETED_WITH_RESIDUAL_CASH",
    "FAILED",
    "NO_ACTION",
})


def acquire_financial_transaction_global_lock_or_raise(
    db: Session,
    *,
    person_id: UUID,
    intent_id: UUID,
    reason: str | None = None,
) -> AcquireGlobalUserTransactionLockResult | None:
    """Acquiert le slot user — flag OFF → no-op strict."""
    if not global_user_transaction_lock_enabled():
        return None
    lock_reason = reason or FINANCIAL_TRANSACTION_GLOBAL_LOCK_REASON
    try:
        return acquire_global_user_transaction_lock(
            db,
            person_id=person_id,
            intent_id=intent_id,
            reason=lock_reason,
        )
    except ProductLockConflict as exc:
        raise transaction_in_progress_409_from_conflict(
            exc,
            existing_reason=lock_reason,
            requested_reason=lock_reason,
        ) from exc


def release_financial_transaction_global_lock(
    db: Session,
    *,
    intent_id: UUID,
    reason: str | None = None,
) -> ReleaseGlobalUserTransactionLockResult:
    return release_global_user_transaction_lock(
        db,
        intent_id=intent_id,
        reason=reason or FINANCIAL_TRANSACTION_GLOBAL_LOCK_REASON,
    )


def release_financial_transaction_global_lock_on_v3_terminal(
    db: Session,
    *,
    intent_id: UUID | None,
    v3_status: str | None,
    reason: str | None = None,
) -> ReleaseGlobalUserTransactionLockResult | None:
    if intent_id is None:
        return None
    status = str(v3_status or "").upper()
    if status not in _V3_TERMINAL_STATUSES:
        return None
    return release_financial_transaction_global_lock(
        db,
        intent_id=intent_id,
        reason=reason,
    )


def release_financial_transaction_global_lock_on_swap_terminal(
    db: Session,
    swap,
    *,
    reason: str | None = None,
) -> ReleaseGlobalUserTransactionLockResult | None:
    """Libère le slot si swap standalone terminal (pas les legs bundle internes)."""
    from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
        is_bundle_internal_swap,
    )
    from services.transaction_intents.repository import TransactionIntentRepository

    if is_bundle_internal_swap(swap):
        return None

    status = str(getattr(swap, "status", "") or "").upper()
    if status not in _SWAP_TERMINAL_STATUSES:
        return None

    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
    )
    if intent is None:
        return None

    return release_financial_transaction_global_lock(
        db,
        intent_id=intent.id,
        reason=reason,
    )
