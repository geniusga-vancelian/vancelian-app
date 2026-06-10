"""Câblage file globale user — swaps LI.FI standalone (hors legs bundle internes)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.product_locks.financial_transaction_global_lock import (
    FINANCIAL_TRANSACTION_GLOBAL_LOCK_REASON,
    acquire_financial_transaction_global_lock_or_raise,
    release_financial_transaction_global_lock_on_swap_terminal,
)
from services.product_locks.global_user_transaction_lock import (
    AcquireGlobalUserTransactionLockResult,
    ReleaseGlobalUserTransactionLockResult,
)
from services.transaction_intents.repository import TransactionIntentRepository

LIFI_SWAP_GLOBAL_LOCK_REASON = "lifi_swap"


def acquire_lifi_swap_global_lock_or_raise(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
) -> AcquireGlobalUserTransactionLockResult | None:
    """Acquiert le slot user au confirm swap — skip legs bundle (lock parent bundle)."""
    swap_repo = PersonWalletSwapRepository()
    swap = swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
    if swap is None:
        return None
    if is_bundle_internal_swap(swap):
        return None

    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
    )
    if intent is None:
        return None

    return acquire_financial_transaction_global_lock_or_raise(
        db,
        person_id=person_id,
        intent_id=intent.id,
        reason=LIFI_SWAP_GLOBAL_LOCK_REASON,
    )


def release_lifi_swap_global_lock_on_terminal(
    db: Session,
    swap,
) -> ReleaseGlobalUserTransactionLockResult | None:
    return release_financial_transaction_global_lock_on_swap_terminal(
        db,
        swap,
        reason=LIFI_SWAP_GLOBAL_LOCK_REASON,
    )
