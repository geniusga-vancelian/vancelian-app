"""Global User Transaction Lock V1 — 1 user = 1 transaction financière active.

Flag ``GLOBAL_USER_TRANSACTION_LOCK_ENABLED`` OFF par défaut · no-op strict.
Indépendant de ``TRANSACTION_PRODUCT_LOCKS_ENABLED`` et des locks fins (S4 L2).
Aucun wiring runtime orchestrator / worker / settlement en V1.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import PersonCryptoWallet
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import ProductLockConflict, TransactionInProgress409
from services.product_locks.global_user_transaction_lock_config import (
    default_global_user_transaction_lock_ttl_seconds,
    global_user_transaction_lock_enabled,
)
from services.product_locks.models import TransactionProductLock

GLOBAL_LOCK_ASSET = "GLOBAL"
GLOBAL_LOCK_WALLET_LABEL = "GLOBAL"
GLOBAL_LOCK_SCOPE = ProductLockScope.FINANCIAL_TRANSACTION
GLOBAL_LOCK_PRODUCT_TYPE = "financial_transaction"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_global_user_transaction_lock_key(*, person_id: UUID) -> str:
    """Clé canonique V1 — wallet/asset logiques GLOBAL (slot DB = wallet canonique)."""
    return (
        f"person:{person_id}:wallet:{GLOBAL_LOCK_WALLET_LABEL}:"
        f"asset:{GLOBAL_LOCK_ASSET}:scope:{GLOBAL_LOCK_SCOPE.value}"
    )


def _resolve_canonical_wallet_id(db: Session, *, person_id: UUID) -> UUID:
    """Wallet de stockage FK — premier wallet personne (slot stable par user)."""
    row = (
        db.query(PersonCryptoWallet)
        .filter(PersonCryptoWallet.person_id == person_id)
        .order_by(PersonCryptoWallet.created_at.asc())
        .first()
    )
    if row is None:
        raise GlobalLockPrerequisiteError(
            "global.lock.missing_wallet",
            f"aucun wallet crypto pour person_id={person_id}",
        )
    return row.id


def _expire_global_locks_for_person(
    db: Session,
    *,
    person_id: UUID,
    now: datetime | None = None,
) -> int:
    ts = now or _utcnow()
    rows = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.person_id == person_id,
            TransactionProductLock.asset == GLOBAL_LOCK_ASSET,
            TransactionProductLock.scope == GLOBAL_LOCK_SCOPE.value,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
            TransactionProductLock.expires_at < ts,
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    for row in rows:
        row.status = ProductLockStatus.EXPIRED.value
    if rows:
        db.flush()
    return len(rows)


def _active_global_lock_query(
    db: Session,
    *,
    person_id: UUID,
    for_update: bool,
):
    q = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.person_id == person_id,
            TransactionProductLock.asset == GLOBAL_LOCK_ASSET,
            TransactionProductLock.scope == GLOBAL_LOCK_SCOPE.value,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
    )
    if for_update:
        q = q.with_for_update()
    return q


class GlobalLockPrerequisiteError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class AcquireGlobalUserTransactionLockResult:
    acquired: bool
    skipped: bool
    idempotent: bool
    lock: TransactionProductLock | None
    reason: str | None = None


@dataclass(frozen=True)
class ReleaseGlobalUserTransactionLockResult:
    released: bool
    skipped: bool
    idempotent: bool
    lock: TransactionProductLock | None
    reason: str | None = None


def transaction_in_progress_409_from_conflict(exc: ProductLockConflict) -> TransactionInProgress409:
    return TransactionInProgress409(
        lock_key=exc.lock_key,
        existing_intent_id=exc.existing_intent_id,
        requested_intent_id=exc.requested_intent_id,
    )


def find_active_global_user_transaction_lock(
    db: Session,
    *,
    person_id: UUID,
) -> TransactionProductLock | None:
    """Retourne le lock global actif non expiré, ou None (flag OFF → None)."""
    if not global_user_transaction_lock_enabled():
        return None

    now = _utcnow()
    _expire_global_locks_for_person(db, person_id=person_id, now=now)
    return _active_global_lock_query(db, person_id=person_id, for_update=False).first()


def acquire_global_user_transaction_lock(
    db: Session,
    *,
    person_id: UUID,
    intent_id: UUID,
    expires_at: datetime | None = None,
    reason: str | None = None,
) -> AcquireGlobalUserTransactionLockResult:
    """Acquiert le lock global user — flag OFF → no-op strict (aucune écriture DB)."""
    if not global_user_transaction_lock_enabled():
        return AcquireGlobalUserTransactionLockResult(
            acquired=False,
            skipped=True,
            idempotent=False,
            lock=None,
            reason=reason,
        )

    lock_key = build_global_user_transaction_lock_key(person_id=person_id)
    wallet_id = _resolve_canonical_wallet_id(db, person_id=person_id)
    now = _utcnow()
    if expires_at is None:
        expires_at = now + timedelta(seconds=default_global_user_transaction_lock_ttl_seconds())

    _expire_global_locks_for_person(db, person_id=person_id, now=now)

    existing = _active_global_lock_query(
        db,
        person_id=person_id,
        for_update=True,
    ).first()

    if existing is not None:
        if existing.intent_id == intent_id:
            return AcquireGlobalUserTransactionLockResult(
                acquired=True,
                skipped=False,
                idempotent=True,
                lock=existing,
                reason=reason,
            )
        raise ProductLockConflict(
            lock_key=lock_key,
            existing_intent_id=existing.intent_id,
            requested_intent_id=intent_id,
        )

    lock = TransactionProductLock(
        person_id=person_id,
        wallet_id=wallet_id,
        asset=GLOBAL_LOCK_ASSET,
        scope=GLOBAL_LOCK_SCOPE.value,
        product_type=GLOBAL_LOCK_PRODUCT_TYPE,
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
        raced = _active_global_lock_query(
            db,
            person_id=person_id,
            for_update=True,
        ).first()
        if raced is None:
            raise
        if raced.intent_id == intent_id:
            return AcquireGlobalUserTransactionLockResult(
                acquired=True,
                skipped=False,
                idempotent=True,
                lock=raced,
                reason=reason,
            )
        raise ProductLockConflict(
            lock_key=lock_key,
            existing_intent_id=raced.intent_id,
            requested_intent_id=intent_id,
        ) from None

    return AcquireGlobalUserTransactionLockResult(
        acquired=True,
        skipped=False,
        idempotent=False,
        lock=lock,
        reason=reason,
    )


def release_global_user_transaction_lock(
    db: Session,
    *,
    intent_id: UUID,
    reason: str | None = None,
) -> ReleaseGlobalUserTransactionLockResult:
    """Libère le lock global pour ``intent_id`` — flag OFF → no-op strict."""
    if not global_user_transaction_lock_enabled():
        return ReleaseGlobalUserTransactionLockResult(
            released=False,
            skipped=True,
            idempotent=False,
            lock=None,
            reason=reason,
        )

    row = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == intent_id,
            TransactionProductLock.asset == GLOBAL_LOCK_ASSET,
            TransactionProductLock.scope == GLOBAL_LOCK_SCOPE.value,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
        .with_for_update()
        .first()
    )

    if row is None:
        released = (
            db.query(TransactionProductLock)
            .filter(
                TransactionProductLock.intent_id == intent_id,
                TransactionProductLock.asset == GLOBAL_LOCK_ASSET,
                TransactionProductLock.scope == GLOBAL_LOCK_SCOPE.value,
                TransactionProductLock.status == ProductLockStatus.RELEASED.value,
            )
            .first()
        )
        if released is not None:
            return ReleaseGlobalUserTransactionLockResult(
                released=True,
                skipped=False,
                idempotent=True,
                lock=released,
                reason=reason,
            )
        return ReleaseGlobalUserTransactionLockResult(
            released=False,
            skipped=False,
            idempotent=False,
            lock=None,
            reason=reason,
        )

    now = _utcnow()
    row.status = ProductLockStatus.RELEASED.value
    row.released_at = now
    db.flush()
    return ReleaseGlobalUserTransactionLockResult(
        released=True,
        skipped=False,
        idempotent=False,
        lock=row,
        reason=reason,
    )
