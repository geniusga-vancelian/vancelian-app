"""Global User Transaction Lock V1 — 1 user = 1 transaction financière active."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.onchain_indexer.models import TransactionIntent
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import ProductLockConflict, TransactionInProgress409
from services.product_locks.global_user_transaction_lock import (
    GLOBAL_LOCK_ASSET,
    GLOBAL_LOCK_SCOPE,
    acquire_global_user_transaction_lock,
    build_global_user_transaction_lock_key,
    find_active_global_user_transaction_lock,
    release_global_user_transaction_lock,
    transaction_in_progress_409_from_conflict,
)
from services.product_locks.models import TransactionProductLock
from services.product_locks.service import acquire_product_lock
from tests.conftest import make_linked_client
from tests.test_product_locks_l2_engine import _migration_175_ready


pytestmark_db = pytest.mark.skipif(
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


def _intent(db: Session, person_id: uuid.UUID, *, product_type: str = "lifi_swap") -> TransactionIntent:
    row = TransactionIntent(
        person_id=person_id,
        product_type=product_type,
        operation_type="swap",
        idempotency_key=f"global-lock-test-{uuid.uuid4()}",
        status="created",
    )
    db.add(row)
    db.flush()
    return row


def _expires_in(seconds: int = 3600) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


@pytest.fixture
def global_lock_on(monkeypatch):
    monkeypatch.setenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", "true")


@pytest.fixture
def global_lock_off(monkeypatch):
    monkeypatch.delenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", raising=False)


@pytestmark_db
def test_flag_off_acquire_is_no_op(db: Session, global_lock_off):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    before = db.execute(sa.text("SELECT COUNT(*) FROM transaction_product_locks")).scalar()
    result = acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent.id,
        expires_at=_expires_in(),
        reason="test_flag_off",
    )
    db.flush()
    after = db.execute(sa.text("SELECT COUNT(*) FROM transaction_product_locks")).scalar()

    assert result.skipped is True
    assert result.acquired is False
    assert result.lock is None
    assert after == before
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None


@pytestmark_db
def test_acquire_nominal(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    result = acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent.id,
        expires_at=_expires_in(),
    )
    db.flush()

    assert result.acquired is True
    assert result.skipped is False
    assert result.idempotent is False
    assert result.lock is not None
    assert result.lock.scope == GLOBAL_LOCK_SCOPE.value
    assert result.lock.asset == GLOBAL_LOCK_ASSET
    assert result.lock.intent_id == intent.id
    assert result.lock.lock_key == build_global_user_transaction_lock_key(person_id=pe.person_id)

    active = find_active_global_user_transaction_lock(db, person_id=pe.person_id)
    assert active is not None
    assert active.id == result.lock.id


@pytestmark_db
def test_same_intent_idempotent(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    first = acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent.id,
        expires_at=_expires_in(),
    )
    db.flush()
    second = acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent.id,
        expires_at=_expires_in(),
    )
    db.flush()

    count = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.person_id == pe.person_id,
            TransactionProductLock.scope == GLOBAL_LOCK_SCOPE.value,
        )
        .count()
    )

    assert first.acquired is True
    assert second.idempotent is True
    assert second.lock.id == first.lock.id
    assert count == 1


@pytestmark_db
def test_second_intent_same_user_conflict(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent_a.id,
        expires_at=_expires_in(),
    )
    db.flush()

    with pytest.raises(ProductLockConflict) as exc:
        acquire_global_user_transaction_lock(
            db,
            person_id=pe.person_id,
            intent_id=intent_b.id,
            expires_at=_expires_in(),
        )
    assert exc.value.existing_intent_id == intent_a.id
    assert exc.value.requested_intent_id == intent_b.id


@pytestmark_db
def test_different_user_allowed(db: Session, global_lock_on):
    pe_a = make_linked_client(db)
    pe_b = make_linked_client(db)
    _wallet(db, pe_a)
    _wallet(db, pe_b)
    intent_a = _intent(db, pe_a.person_id)
    intent_b = _intent(db, pe_b.person_id)

    acquire_global_user_transaction_lock(
        db,
        person_id=pe_a.person_id,
        intent_id=intent_a.id,
        expires_at=_expires_in(),
    )
    result_b = acquire_global_user_transaction_lock(
        db,
        person_id=pe_b.person_id,
        intent_id=intent_b.id,
        expires_at=_expires_in(),
    )
    db.flush()

    assert result_b.acquired is True
    assert find_active_global_user_transaction_lock(db, person_id=pe_a.person_id) is not None
    assert find_active_global_user_transaction_lock(db, person_id=pe_b.person_id) is not None


@pytestmark_db
def test_release_success(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent.id,
        expires_at=_expires_in(),
    )
    db.flush()

    released = release_global_user_transaction_lock(db, intent_id=intent.id, reason="done")
    db.flush()

    assert released.released is True
    assert released.idempotent is False
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None


@pytestmark_db
def test_release_idempotent(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent.id,
        expires_at=_expires_in(),
    )
    db.flush()
    first = release_global_user_transaction_lock(db, intent_id=intent.id)
    second = release_global_user_transaction_lock(db, intent_id=intent.id)
    db.flush()

    assert first.released is True
    assert second.idempotent is True


@pytestmark_db
def test_expired_lock_ignored_after_cleanup(db: Session, global_lock_on):
    pe = make_linked_client(db)
    wallet = _wallet(db, pe)
    intent_old = _intent(db, pe.person_id)
    intent_new = _intent(db, pe.person_id)

    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    row = TransactionProductLock(
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset=GLOBAL_LOCK_ASSET,
        scope=GLOBAL_LOCK_SCOPE.value,
        product_type="financial_transaction",
        intent_id=intent_old.id,
        status=ProductLockStatus.ACTIVE.value,
        lock_key=build_global_user_transaction_lock_key(person_id=pe.person_id),
        expires_at=past,
    )
    db.add(row)
    db.flush()

    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None

    result = acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent_new.id,
        expires_at=_expires_in(),
    )
    db.flush()

    assert result.acquired is True
    assert result.lock.intent_id == intent_new.id


@pytestmark_db
def test_coexists_with_fine_grained_locks(db: Session, global_lock_on, monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")
    pe = make_linked_client(db)
    wallet = _wallet(db, pe)
    intent_global = _intent(db, pe.person_id, product_type="bundle_invest")
    intent_fine = _intent(db, pe.person_id)

    global_result = acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent_global.id,
        expires_at=_expires_in(),
    )
    fine_result = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent_fine.id,
    )
    db.flush()

    assert global_result.acquired is True
    assert fine_result.acquired is True


@pytestmark_db
def test_conflict_maps_to_transaction_in_progress_409(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent_a.id,
        expires_at=_expires_in(),
    )
    db.flush()

    with pytest.raises(ProductLockConflict) as exc:
        acquire_global_user_transaction_lock(
            db,
            person_id=pe.person_id,
            intent_id=intent_b.id,
            expires_at=_expires_in(),
        )

    mapped = transaction_in_progress_409_from_conflict(exc.value)
    assert isinstance(mapped, TransactionInProgress409)
    assert mapped.error_code == "transaction_in_progress"
    assert mapped.http_status == 409


def test_no_settlement_worker_controller_imports_in_module_source():
    import services.product_locks.global_user_transaction_lock as mod

    text = inspect.getsource(mod).lower()
    forbidden = (
        "transaction_outbox",
        "settlement_worker",
        "lifi_swap_controller",
        "reconcile_lifi_swap",
        "services.settlement.settle",
        "bundle_leg_settlement_handler",
        "settle_bundle_leg",
    )
    for token in forbidden:
        assert token not in text, token
