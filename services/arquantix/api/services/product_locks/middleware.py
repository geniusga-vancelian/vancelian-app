"""Validation middleware S4 (L4a — non branché runtime)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from services.product_locks.balance_snapshot import (
    BalanceSnapshot,
    compute_balance_snapshot_hash,
)
from services.product_locks.config import transaction_product_locks_enabled
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import (
    BalanceChanged409,
    BalanceVersionMismatch409,
    ProductLockConflict409,
)
from services.product_locks.models import TransactionProductLock


def _normalize_asset(asset: str) -> str:
    return str(asset).strip().upper()


def _normalize_scope(scope: ProductLockScope | str) -> str:
    if isinstance(scope, ProductLockScope):
        return scope.value
    return str(scope).strip().lower()


def _coerce_snapshot(stored_snapshot: BalanceSnapshot | Mapping[str, Any]) -> BalanceSnapshot:
    if isinstance(stored_snapshot, BalanceSnapshot):
        return stored_snapshot
    return BalanceSnapshot(
        asset=str(stored_snapshot["asset"]),
        available=str(stored_snapshot["available"]),
        version=int(stored_snapshot["version"]),
        hash=str(stored_snapshot["hash"]),
    )


@dataclass(frozen=True)
class ProductLockMiddlewareResult:
    skipped: bool
    ok: bool


def validate_product_lock_or_raise(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: ProductLockScope | str,
    intent_id: UUID,
) -> ProductLockMiddlewareResult:
    """Vérifie qu'aucun lock actif d'un autre intent n'occupe le slot.

    Flag OFF → no-op (aucune requête bloquante · aucune exception).
    """
    if not transaction_product_locks_enabled():
        return ProductLockMiddlewareResult(skipped=True, ok=True)

    asset_norm = _normalize_asset(asset)
    scope_norm = _normalize_scope(scope)

    row = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.person_id == person_id,
            TransactionProductLock.wallet_id == wallet_id,
            TransactionProductLock.asset == asset_norm,
            TransactionProductLock.scope == scope_norm,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
        .first()
    )

    if row is None or row.intent_id == intent_id:
        return ProductLockMiddlewareResult(skipped=False, ok=True)

    raise ProductLockConflict409(
        lock_key=row.lock_key,
        existing_intent_id=row.intent_id,
        requested_intent_id=intent_id,
    )


def validate_balance_snapshot_or_raise(
    *,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: ProductLockScope | str,
    stored_snapshot: BalanceSnapshot | Mapping[str, Any],
    current_available: str,
    current_version: int,
) -> ProductLockMiddlewareResult:
    """Re-vérifie version + hash snapshot avant transition vers PROCESSING.

    Flag OFF → no-op.
    Version drift → ``BalanceVersionMismatch409``.
    Hash drift → ``BalanceChanged409``.
    """
    if not transaction_product_locks_enabled():
        return ProductLockMiddlewareResult(skipped=True, ok=True)

    asset_norm = _normalize_asset(asset)
    scope_norm = _normalize_scope(scope)
    snapshot = _coerce_snapshot(stored_snapshot)

    if int(snapshot.version) != int(current_version):
        raise BalanceVersionMismatch409(
            asset=asset_norm,
            scope=scope_norm,
            expected_version=int(snapshot.version),
            actual_version=int(current_version),
        )

    actual_hash = compute_balance_snapshot_hash(
        person_id=person_id,
        wallet_id=wallet_id,
        asset=asset_norm,
        scope=scope_norm,
        available=current_available,
        version=int(current_version),
    )
    if actual_hash != snapshot.hash:
        raise BalanceChanged409(
            asset=asset_norm,
            scope=scope_norm,
            expected_hash=snapshot.hash,
            actual_hash=actual_hash,
        )

    return ProductLockMiddlewareResult(skipped=False, ok=True)
