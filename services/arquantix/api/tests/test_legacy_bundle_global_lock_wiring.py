"""Global User Transaction Lock — wiring legacy Bundle Invest WebApp."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.legacy_bundle_global_lock import (
    LEGACY_BUNDLE_INVEST_REASON,
    acquire_legacy_bundle_global_lock_or_raise,
    release_legacy_bundle_global_lock,
    release_legacy_bundle_global_lock_on_terminal,
    transaction_in_progress_response_body,
)
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import (
    TRANSACTION_IN_PROGRESS_USER_MESSAGE,
    TransactionInProgress409,
)
from services.product_locks.global_user_transaction_lock import (
    acquire_global_user_transaction_lock,
    find_active_global_user_transaction_lock,
)
from services.product_locks.models import TransactionProductLock
from tests.conftest import make_linked_client
from tests.test_product_locks_l2_engine import _migration_175_ready


pytestmark = [
    pytest.mark.skipif(not _migration_175_ready(), reason="Migration 175 requise."),
]


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


def _intent(db: Session, person_id: uuid.UUID, *, product_type: str = "bundle_invest") -> TransactionIntent:
    row = TransactionIntent(
        person_id=person_id,
        product_type=product_type,
        operation_type="invest",
        idempotency_key=f"legacy-bundle-lock-{uuid.uuid4()}",
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


def test_flag_off_acquire_is_no_op(db: Session, global_lock_off):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    before = db.execute(sa.text("SELECT COUNT(*) FROM transaction_product_locks")).scalar()
    result = acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    db.flush()
    after = db.execute(sa.text("SELECT COUNT(*) FROM transaction_product_locks")).scalar()

    assert result is None
    assert after == before


def test_flag_on_first_bundle_acquires_lock(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    result = acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    db.flush()

    assert result is not None
    assert result.acquired is True
    active = find_active_global_user_transaction_lock(db, person_id=pe.person_id)
    assert active is not None
    assert active.intent_id == intent.id
    assert active.scope == ProductLockScope.FINANCIAL_TRANSACTION.value


def test_second_bundle_different_portfolio_same_user_409(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent_a.id,
    )
    db.flush()

    with pytest.raises(TransactionInProgress409) as exc_info:
        acquire_legacy_bundle_global_lock_or_raise(
            db, person_id=pe.person_id, intent_id=intent_b.id,
        )

    assert exc_info.value.error_code == "transaction_in_progress"
    assert str(exc_info.value) == TRANSACTION_IN_PROGRESS_USER_MESSAGE


def test_same_batch_resume_idempotent(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    first = acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    second = acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    db.flush()

    assert first is not None and first.acquired is True
    assert second is not None and second.idempotent is True
    count = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.person_id == pe.person_id,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        )
        .count()
    )
    assert count == 1


def test_release_on_completed_terminal_mode(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    db.flush()

    result = release_legacy_bundle_global_lock_on_terminal(
        db, intent_id=intent.id, mode="clear",
    )
    db.flush()

    assert result is not None
    assert result.released is True
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None


def test_release_on_terminal_failure(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    db.flush()

    result = release_legacy_bundle_global_lock_on_terminal(
        db, intent_id=intent.id, mode="release_failed",
    )
    db.flush()

    assert result is not None
    assert result.released is True


def test_lock_not_released_while_pending_mode(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    db.flush()

    result = release_legacy_bundle_global_lock_on_terminal(
        db, intent_id=intent.id, mode="keep",
    )
    db.flush()

    assert result is None
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is not None


def test_terminal_bundle_invest_lock_releases_global(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=intent.id,
        expires_at=_expires_in(),
        reason=LEGACY_BUNDLE_INVEST_REASON,
    )
    db.flush()

    BundleOrchestrator._terminal_bundle_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=uuid.uuid4(),
        batch_id=str(uuid.uuid4()),
        parent_intent_id=intent.id,
        mode="clear",
    )
    db.flush()

    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None


def test_no_pe_cb_mutation_from_lock_acquire(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent = _intent(db, pe.person_id)

    pe_before = db.execute(sa.text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
    cb_before = db.execute(sa.text("SELECT COUNT(*) FROM pe_cost_basis_entries")).scalar()

    acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent.id,
    )
    db.flush()

    pe_after = db.execute(sa.text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
    cb_after = db.execute(sa.text("SELECT COUNT(*) FROM pe_cost_basis_entries")).scalar()

    assert pe_after == pe_before
    assert cb_after == cb_before


def test_409_response_body_user_safe(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent_a.id,
    )
    db.flush()

    with pytest.raises(TransactionInProgress409) as exc_info:
        acquire_legacy_bundle_global_lock_or_raise(
            db, person_id=pe.person_id, intent_id=intent_b.id,
        )

    body = transaction_in_progress_response_body(exc_info.value)
    assert body["status"] == "transaction_in_progress"
    assert body["error_code"] == "transaction_in_progress"
    assert body["message"] == TRANSACTION_IN_PROGRESS_USER_MESSAGE
    assert "existing_intent_id" not in body
    assert "requested_intent_id" not in body
    assert exc_info.value.existing_intent_id == intent_a.id
    assert exc_info.value.requested_intent_id == intent_b.id


def test_release_after_first_allows_second(db: Session, global_lock_on):
    pe = make_linked_client(db)
    _wallet(db, pe)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent_a.id,
    )
    db.flush()
    release_legacy_bundle_global_lock(db, intent_id=intent_a.id)
    db.flush()

    second = acquire_legacy_bundle_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent_b.id,
    )
    db.flush()

    assert second is not None
    assert second.acquired is True
