"""Acquisition / release S4 product locks (L2 — non branché runtime)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.product_locks.config import (
    default_product_lock_ttl_seconds,
    transaction_product_locks_enabled,
)
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import ProductLockConflict
from services.product_locks.lock_key import build_lock_key
from services.product_locks.models import TransactionProductLock
from services.product_locks.results import (
    AcquireProductLockResult,
    ReleaseProductLockResult,
    ReleaseProductLocksForIntentResult,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_asset(asset: str) -> str:
    return str(asset).strip().upper()


def _normalize_scope(scope: ProductLockScope | str) -> str:
    if isinstance(scope, ProductLockScope):
        return scope.value
    return str(scope).strip().lower()


def _active_lock_query(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: str,
    for_update: bool,
):
    q = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.person_id == person_id,
            TransactionProductLock.wallet_id == wallet_id,
            TransactionProductLock.asset == asset,
            TransactionProductLock.scope == scope,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
    )
    if for_update:
        q = q.with_for_update()
    return q


def expire_product_locks(
    db: Session,
    *,
    now: datetime | None = None,
    person_id: UUID | None = None,
    wallet_id: UUID | None = None,
    asset: str | None = None,
    scope: ProductLockScope | str | None = None,
) -> int:
    """Marque ``expired`` les locks actifs dont ``expires_at`` est dépassé."""
    if not transaction_product_locks_enabled():
        return 0

    ts = now or _utcnow()
    q = db.query(TransactionProductLock).filter(
        TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        TransactionProductLock.released_at.is_(None),
        TransactionProductLock.expires_at < ts,
    )
    if person_id is not None:
        q = q.filter(TransactionProductLock.person_id == person_id)
    if wallet_id is not None:
        q = q.filter(TransactionProductLock.wallet_id == wallet_id)
    if asset is not None:
        q = q.filter(TransactionProductLock.asset == _normalize_asset(asset))
    if scope is not None:
        q = q.filter(TransactionProductLock.scope == _normalize_scope(scope))

    rows = q.with_for_update(skip_locked=True).all()
    for row in rows:
        row.status = ProductLockStatus.EXPIRED.value
    if rows:
        db.flush()
    return len(rows)


def acquire_product_lock(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: ProductLockScope | str,
    product_type: str,
    intent_id: UUID,
    expires_at: datetime | None = None,
    ttl_seconds: int | None = None,
) -> AcquireProductLockResult:
    """Acquiert un lock exclusif sur ``person + wallet + asset + scope``.

    Flag OFF → no-op (aucune écriture DB).
    Même intent → idempotent success.
    Autre intent actif sur le slot → ``ProductLockConflict``.
    """
    if not transaction_product_locks_enabled():
        return AcquireProductLockResult(
            acquired=False,
            skipped=True,
            idempotent=False,
            lock=None,
        )

    asset_norm = _normalize_asset(asset)
    scope_norm = _normalize_scope(scope)
    lock_key = build_lock_key(
        person_id=person_id,
        wallet_id=wallet_id,
        asset=asset_norm,
        scope=scope_norm,
    )
    now = _utcnow()
    if expires_at is None:
        ttl = ttl_seconds if ttl_seconds is not None else default_product_lock_ttl_seconds()
        expires_at = now + timedelta(seconds=ttl)

    expire_product_locks(
        db,
        now=now,
        person_id=person_id,
        wallet_id=wallet_id,
        asset=asset_norm,
        scope=scope_norm,
    )

    existing = _active_lock_query(
        db,
        person_id=person_id,
        wallet_id=wallet_id,
        asset=asset_norm,
        scope=scope_norm,
        for_update=True,
    ).first()

    if existing is not None:
        if existing.intent_id == intent_id:
            return AcquireProductLockResult(
                acquired=True,
                skipped=False,
                idempotent=True,
                lock=existing,
            )
        raise ProductLockConflict(
            lock_key=lock_key,
            existing_intent_id=existing.intent_id,
            requested_intent_id=intent_id,
        )

    lock = TransactionProductLock(
        person_id=person_id,
        wallet_id=wallet_id,
        asset=asset_norm,
        scope=scope_norm,
        product_type=str(product_type).strip(),
        intent_id=intent_id,
        status=ProductLockStatus.ACTIVE.value,
        lock_key=lock_key,
        expires_at=expires_at,
    )
    savepoint = db.begin_nested()
    try:
        db.add(lock)
        db.flush()
    except IntegrityError:
        savepoint.rollback()
        raced = _active_lock_query(
            db,
            person_id=person_id,
            wallet_id=wallet_id,
            asset=asset_norm,
            scope=scope_norm,
            for_update=True,
        ).first()
        if raced is None:
            raise
        if raced.intent_id == intent_id:
            return AcquireProductLockResult(
                acquired=True,
                skipped=False,
                idempotent=True,
                lock=raced,
            )
        raise ProductLockConflict(
            lock_key=lock_key,
            existing_intent_id=raced.intent_id,
            requested_intent_id=intent_id,
        ) from None

    return AcquireProductLockResult(
        acquired=True,
        skipped=False,
        idempotent=False,
        lock=lock,
    )


def release_product_lock(
    db: Session,
    *,
    intent_id: UUID,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: ProductLockScope | str,
) -> ReleaseProductLockResult:
    """Libère un lock actif pour l'intent et le slot donnés."""
    if not transaction_product_locks_enabled():
        return ReleaseProductLockResult(
            released=False,
            skipped=True,
            idempotent=False,
            lock=None,
        )

    asset_norm = _normalize_asset(asset)
    scope_norm = _normalize_scope(scope)

    row = _active_lock_query(
        db,
        person_id=person_id,
        wallet_id=wallet_id,
        asset=asset_norm,
        scope=scope_norm,
        for_update=True,
    ).filter(TransactionProductLock.intent_id == intent_id).first()

    if row is None:
        released = (
            db.query(TransactionProductLock)
            .filter(
                TransactionProductLock.intent_id == intent_id,
                TransactionProductLock.person_id == person_id,
                TransactionProductLock.wallet_id == wallet_id,
                TransactionProductLock.asset == asset_norm,
                TransactionProductLock.scope == scope_norm,
                TransactionProductLock.status == ProductLockStatus.RELEASED.value,
            )
            .first()
        )
        if released is not None:
            return ReleaseProductLockResult(
                released=True,
                skipped=False,
                idempotent=True,
                lock=released,
            )
        return ReleaseProductLockResult(
            released=False,
            skipped=False,
            idempotent=False,
            lock=None,
        )

    now = _utcnow()
    row.status = ProductLockStatus.RELEASED.value
    row.released_at = now
    db.flush()
    return ReleaseProductLockResult(
        released=True,
        skipped=False,
        idempotent=False,
        lock=row,
    )


def release_product_locks_for_intent(
    db: Session,
    *,
    intent_id: UUID,
    reason: str | None = None,
) -> ReleaseProductLocksForIntentResult:
    """Libère tous les locks actifs liés à ``intent_id``.

    Flag OFF → no-op strict (aucune écriture DB).
    Idempotent : locks déjà ``released`` ne sont pas re-modifiés ;
    un second appel après release complète retourne ``idempotent=True``.
    ``reason`` est documentaire (logging) — pas de colonne metadata dédiée en L1.
    """
    if not transaction_product_locks_enabled():
        return ReleaseProductLocksForIntentResult(
            released_count=0,
            skipped=True,
            idempotent=False,
        )

    active_rows = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == intent_id,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
        .with_for_update()
        .all()
    )

    if not active_rows:
        already_released = (
            db.query(TransactionProductLock)
            .filter(
                TransactionProductLock.intent_id == intent_id,
                TransactionProductLock.status == ProductLockStatus.RELEASED.value,
            )
            .count()
        )
        return ReleaseProductLocksForIntentResult(
            released_count=0,
            skipped=False,
            idempotent=already_released > 0,
            already_released_count=already_released,
        )

    now = _utcnow()
    for row in active_rows:
        row.status = ProductLockStatus.RELEASED.value
        row.released_at = now
    db.flush()

    return ReleaseProductLocksForIntentResult(
        released_count=len(active_rows),
        skipped=False,
        idempotent=False,
    )
