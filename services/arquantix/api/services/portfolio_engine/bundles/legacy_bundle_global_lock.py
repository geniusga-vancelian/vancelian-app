"""Global User Transaction Lock — chemin legacy Bundle Invest WebApp (LI.FI).

Flag ``GLOBAL_USER_TRANSACTION_LOCK_ENABLED`` OFF → no-op strict (comportement prod inchangé).
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

LEGACY_BUNDLE_INVEST_REASON = "legacy_bundle_invest"

_TERMINAL_RELEASE_MODES = frozenset({"clear", "release_failed"})


def acquire_legacy_bundle_global_lock_or_raise(
    db: Session,
    *,
    person_id: UUID,
    intent_id: UUID,
) -> AcquireGlobalUserTransactionLockResult | None:
    """Acquiert le lock global user pour un bundle invest legacy — flag OFF → None."""
    if not global_user_transaction_lock_enabled():
        return None
    try:
        return acquire_global_user_transaction_lock(
            db,
            person_id=person_id,
            intent_id=intent_id,
            reason=LEGACY_BUNDLE_INVEST_REASON,
        )
    except ProductLockConflict as exc:
        raise transaction_in_progress_409_from_conflict(
            exc,
            existing_reason=LEGACY_BUNDLE_INVEST_REASON,
            requested_reason=LEGACY_BUNDLE_INVEST_REASON,
        ) from exc


def release_legacy_bundle_global_lock(
    db: Session,
    *,
    intent_id: UUID,
) -> ReleaseGlobalUserTransactionLockResult:
    return release_global_user_transaction_lock(
        db,
        intent_id=intent_id,
        reason=LEGACY_BUNDLE_INVEST_REASON,
    )


def release_legacy_bundle_global_lock_on_terminal(
    db: Session,
    *,
    intent_id: UUID | None,
    mode: str,
) -> ReleaseGlobalUserTransactionLockResult | None:
    """Release global lock sur état terminal bundle — pas pendant pending signature."""
    if intent_id is None or mode not in _TERMINAL_RELEASE_MODES:
        return None
    return release_legacy_bundle_global_lock(db, intent_id=intent_id)


def transaction_in_progress_response_body(exc: TransactionInProgress409) -> dict:
    """Body public 409 — pas d'identifiants internes (intent_id réservés à l'exception/logs)."""
    return {
        "status": "transaction_in_progress",
        "error_code": exc.error_code,
        "message": str(exc),
    }
