"""S4d — partitionnement séquentiel de la file ``intent.created`` par lock_key."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.product_locks.allowlist import product_locks_enabled_for_person
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.lock_key import build_lock_key
from services.product_locks.models import TransactionProductLock
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.orchestrator_product_locks import (
    _is_orchestrator_lifi_intent,
    _resolve_orchestrator_wallet_id,
    _source_asset,
)


def resolve_orchestrator_intent_lock_key(db: Session, intent: TransactionIntent) -> str | None:
    """Clé de queue Product Locks pour un intent orchestrateur LI.FI, ou ``None`` si hors scope lock."""
    if not _is_orchestrator_lifi_intent(intent):
        return None
    if not product_locks_enabled_for_person(db, intent.person_id):
        return None
    wallet_id = _resolve_orchestrator_wallet_id(db, intent.person_id)
    asset = _source_asset(intent)
    return build_lock_key(
        person_id=intent.person_id,
        wallet_id=wallet_id,
        asset=asset,
        scope=ProductLockScope.TRADING_AVAILABLE,
    )


def lock_key_has_active_lock(db: Session, lock_key: str) -> bool:
    return (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.lock_key == lock_key,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
        .count()
        > 0
    )


def partition_intent_created_events(
    db: Session,
    events: list[TransactionOutbox],
) -> tuple[list[TransactionOutbox], list[TransactionOutbox]]:
    """Retourne (à traiter, différés) — au plus un event par ``lock_key`` par batch.

    Un event est différé si :
    - un autre event du batch cible déjà le même ``lock_key`` ;
    - un lock actif existe déjà en base pour ce ``lock_key`` (intent précédent pas encore released).
    """
    to_process: list[TransactionOutbox] = []
    deferred: list[TransactionOutbox] = []
    seen_lock_keys: set[str] = set()

    for event in events:
        intent = (
            db.query(TransactionIntent).filter(TransactionIntent.id == event.intent_id).first()
        )
        if intent is None:
            to_process.append(event)
            continue

        lock_key = resolve_orchestrator_intent_lock_key(db, intent)
        if lock_key is None:
            to_process.append(event)
            continue

        if lock_key in seen_lock_keys or lock_key_has_active_lock(db, lock_key):
            deferred.append(event)
            continue

        seen_lock_keys.add(lock_key)
        to_process.append(event)

    return to_process, deferred
