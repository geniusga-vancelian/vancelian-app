"""S4 L2 — acquire / release product lock engine (migration 175)."""
from __future__ import annotations

import pathlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.onchain_indexer.models import TransactionIntent
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import ProductLockConflict
from services.product_locks.models import TransactionProductLock
from services.product_locks.service import (
    acquire_product_lock,
    expire_product_locks,
    release_product_lock,
)
from tests.conftest import make_linked_client


def _migration_175_ready() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_product_locks'"
                )
            ).fetchone()
            return row is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_175_ready(),
    reason="Migration 175 requise (transaction_product_locks).",
)


def _wallet(db: Session, pe_client):
    return upsert_person_crypto_wallet(
        db,
        person_id=pe_client.person_id,
        pe_client_id=pe_client.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )


def _intent(db: Session, person_id) -> TransactionIntent:
    intent = TransactionIntent(
        person_id=person_id,
        product_type="lifi_swap",
        operation_type="swap",
        idempotency_key=f"test-lock-{uuid.uuid4()}",
        status="created",
    )
    db.add(intent)
    db.flush()
    return intent


def _slot(db: Session):
    pe = make_linked_client(db)
    wallet = _wallet(db, pe)
    return pe, wallet


@pytest.fixture
def locks_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")


@pytest.fixture
def locks_off(monkeypatch):
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", raising=False)


def test_flag_off_acquire_is_no_op(db: Session, locks_off):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    result = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent.id,
    )

    assert result.skipped is True
    assert result.acquired is False
    assert result.lock is None
    assert db.query(TransactionProductLock).count() == 0


def test_flag_off_release_is_no_op(db: Session, locks_off):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    result = release_product_lock(
        db,
        intent_id=intent.id,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )

    assert result.skipped is True
    assert result.released is False


def test_acquire_new_lock_active(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    result = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="usdc",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent.id,
    )

    assert result.acquired is True
    assert result.skipped is False
    assert result.idempotent is False
    assert result.lock is not None
    assert result.lock.status == ProductLockStatus.ACTIVE.value
    assert result.lock.asset == "USDC"
    assert result.lock.released_at is None
    assert result.lock.expires_at is not None


def test_acquire_same_intent_idempotent(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    first = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent.id,
    )
    second = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent.id,
    )

    assert first.lock is not None
    assert second.idempotent is True
    assert second.lock.id == first.lock.id
    assert db.query(TransactionProductLock).count() == 1


def test_acquire_other_intent_same_slot_conflict(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent_a.id,
    )

    with pytest.raises(ProductLockConflict) as exc:
        acquire_product_lock(
            db,
            person_id=pe.person_id,
            wallet_id=wallet.id,
            asset="USDC",
            scope=ProductLockScope.TRADING_AVAILABLE,
            product_type="bundle_invest",
            intent_id=intent_b.id,
        )

    assert exc.value.existing_intent_id == intent_a.id
    assert exc.value.requested_intent_id == intent_b.id
    assert db.query(TransactionProductLock).count() == 1


def test_acquire_different_scope_allowed(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent_a.id,
    )
    second = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.BUNDLE,
        product_type="bundle_invest",
        intent_id=intent_b.id,
    )

    assert second.acquired is True
    assert db.query(TransactionProductLock).count() == 2


def test_release_lock_sets_released(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    acquired = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent.id,
    )
    released = release_product_lock(
        db,
        intent_id=intent.id,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )

    assert released.released is True
    assert released.lock is not None
    assert released.lock.status == ProductLockStatus.RELEASED.value
    assert released.lock.released_at is not None
    assert acquired.lock.id == released.lock.id


def test_release_idempotent(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent.id,
    )
    first = release_product_lock(
        db,
        intent_id=intent.id,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )
    second = release_product_lock(
        db,
        intent_id=intent.id,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )

    assert first.released is True
    assert second.idempotent is True


def test_expired_lock_allows_new_acquire(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent_old = _intent(db, pe.person_id)
    intent_new = _intent(db, pe.person_id)
    past = datetime.now(timezone.utc) - timedelta(minutes=5)

    old_lock = TransactionProductLock(
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE.value,
        product_type="lifi_swap",
        intent_id=intent_old.id,
        status=ProductLockStatus.ACTIVE.value,
        lock_key=f"person:{pe.person_id}:wallet:{wallet.id}:asset:USDC:scope:trading_available",
        expires_at=past,
    )
    db.add(old_lock)
    db.flush()

    n = expire_product_locks(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )
    assert n == 1

    result = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent_new.id,
    )

    assert result.acquired is True
    assert result.lock.intent_id == intent_new.id
    active = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
        .count()
    )
    assert active == 1


def test_acquire_after_release_allows_other_intent(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent_a.id,
    )
    release_product_lock(
        db,
        intent_id=intent_a.id,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )
    second = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent_b.id,
    )

    assert second.acquired is True
    assert second.lock.intent_id == intent_b.id


def test_service_module_has_no_runtime_wiring_imports():
    root = pathlib.Path(__file__).resolve().parents[1] / "services" / "product_locks"
    forbidden = ("services.lifi", "services.settlement", "transaction_outbox")
    for name in ("config.py", "service.py", "exceptions.py", "results.py", "lock_key.py"):
        source = (root / name).read_text()
        for token in forbidden:
            assert token not in source, f"{name} must not reference {token}"
