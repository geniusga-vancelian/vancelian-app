"""Global User Transaction Lock — flux bundle transaction V3 (dépôt + rebalance)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.product_locks.financial_transaction_global_lock import (
    acquire_financial_transaction_global_lock_or_raise,
    release_financial_transaction_global_lock,
    release_financial_transaction_global_lock_on_v3_terminal,
)
from services.product_locks.global_user_transaction_lock import (
    AcquireGlobalUserTransactionLockResult,
    ReleaseGlobalUserTransactionLockResult,
)

BUNDLE_TRANSACTION_GLOBAL_LOCK_REASON = "bundle_transaction_v3"


def acquire_bundle_transaction_global_lock_or_raise(
    db: Session,
    *,
    person_id: UUID,
    intent_id: UUID,
) -> AcquireGlobalUserTransactionLockResult | None:
    return acquire_financial_transaction_global_lock_or_raise(
        db,
        person_id=person_id,
        intent_id=intent_id,
        reason=BUNDLE_TRANSACTION_GLOBAL_LOCK_REASON,
    )


def release_bundle_transaction_global_lock(
    db: Session,
    *,
    intent_id: UUID,
) -> ReleaseGlobalUserTransactionLockResult:
    return release_financial_transaction_global_lock(
        db,
        intent_id=intent_id,
        reason=BUNDLE_TRANSACTION_GLOBAL_LOCK_REASON,
    )


def release_bundle_transaction_global_lock_on_v3_terminal(
    db: Session,
    *,
    intent_id: UUID | None,
    v3_status: str | None,
) -> ReleaseGlobalUserTransactionLockResult | None:
    return release_financial_transaction_global_lock_on_v3_terminal(
        db,
        intent_id=intent_id,
        v3_status=v3_status,
        reason=BUNDLE_TRANSACTION_GLOBAL_LOCK_REASON,
    )
