"""S4 L4c — release product lock lifecycle (flag OFF par défaut)."""
from __future__ import annotations

import pathlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    link_external_identity_to_person,
    upsert_person_crypto_wallet,
)
from services.lifi.enums import SwapSessionStatus
from services.onchain_indexer.models import TransactionIntent
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.models import TransactionProductLock
from services.product_locks.service import (
    acquire_product_lock,
    release_product_locks_for_intent,
)
from services.transaction_intents.enums import IntentStatus
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.orchestrator_product_locks import (
    apply_orchestrator_product_locks_before_queued,
    release_orchestrator_product_locks_for_intent,
)
from services.transaction_outbox.repository import TransactionOutboxRepository
from services.transaction_outbox.settlement_worker import (
    handle_intent_settle_event,
    process_transaction_outbox_intent_settle,
)
from services.transaction_outbox.worker import (
    handle_intent_created_event,
    process_transaction_outbox_intent_created,
)
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.product_locks_test_utils import enable_product_locks_allowlist
from tests.test_product_locks_l2_engine import _migration_175_ready
from tests.test_transaction_outbox_worker_s2b import _economic_counts, _migration_173_ready


EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
TX_HASH = "0xl4ctest1234567890abcdef1234567890abcdef1234567890abcdef123456"


pytestmark = [
    pytest.mark.skipif(not _migration_173_ready(), reason="Migration 173 requise."),
    pytest.mark.skipif(not _migration_175_ready(), reason="Migration 175 requise."),
]


@pytest.fixture
def locks_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")


@pytest.fixture
def locks_off(monkeypatch):
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", raising=False)


def _wallet(db: Session, pe_client):
    link_external_identity_to_person(
        db,
        person_id=pe_client.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"did:privy:l4c-{uuid.uuid4().hex[:8]}",
        external_email=getattr(pe_client, "email", None) or "l4c@test.local",
    )
    return upsert_person_crypto_wallet(
        db,
        person_id=pe_client.person_id,
        pe_client_id=pe_client.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-l4c"},
    )


def _intent(db: Session, person_id) -> TransactionIntent:
    intent = TransactionIntent(
        person_id=person_id,
        product_type="lifi_swap",
        operation_type="swap",
        idempotency_key=f"test-lock-release-{uuid.uuid4()}",
        status="created",
    )
    db.add(intent)
    db.flush()
    return intent


def _seed_orchestrator_intent(db: Session, monkeypatch):
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    enable_product_locks_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    _wallet(db, pe)
    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("25"),
    )
    db.commit()
    return pe, bundle


def _seed_queued_with_lock(db: Session, monkeypatch):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)
    assert process_transaction_outbox_intent_created(db)["processed"] == 1
    db.refresh(bundle.intent)
    assert bundle.intent.current_phase == IntentOrchestratorPhase.QUEUED.value
    lock = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == bundle.intent.id,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        )
        .one()
    )
    settle_outbox = TransactionOutboxRepository.insert_event(
        db,
        intent_id=bundle.intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
        payload_json={"l4c": True},
    )
    db.commit()
    return pe, bundle, lock, settle_outbox


def _seed_queued_with_lock_confirmed_swap(db: Session, monkeypatch):
    pe, bundle, lock, settle_outbox = _seed_queued_with_lock(db, monkeypatch)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="50",
            chain_id=8453,
        ),
    )
    bundle.swap.status = SwapSessionStatus.CONFIRMED.value
    bundle.swap.tx_hash = TX_HASH
    bundle.swap.estimated_receive = Decimal("0.00475")
    bundle.swap.confirmed_at = datetime.now(timezone.utc)
    bundle.swap.audit_log = [
        {"event": "quote_requested", "signing_wallet_address": EVM_ADDR},
    ]
    bundle.intent.assets_json = {
        "from": {"asset": "USDC", "amount": "25"},
        "to": {"asset": "ETH", "amount": "0.00475"},
    }
    db.commit()
    return pe, bundle, lock, settle_outbox


def test_l4c_release_active_locks_for_intent(db: Session, locks_on):
    pe = make_linked_client(db)
    wallet = _wallet(db, pe)
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
    db.commit()

    first = release_product_locks_for_intent(db, intent_id=intent.id, reason="test")
    assert first.skipped is False
    assert first.released_count == 1
    assert first.idempotent is False

    second = release_product_locks_for_intent(db, intent_id=intent.id, reason="test")
    assert second.released_count == 0
    assert second.idempotent is True


def test_l4c_other_intent_lock_untouched(db: Session, locks_on):
    pe = make_linked_client(db)
    wallet = _wallet(db, pe)
    first_intent = _intent(db, pe.person_id)
    second_intent = _intent(db, pe.person_id)
    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=first_intent.id,
    )
    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="EURC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=second_intent.id,
    )
    db.commit()

    release_product_locks_for_intent(db, intent_id=first_intent.id, reason="test")
    db.commit()

    assert (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == first_intent.id,
            TransactionProductLock.status == ProductLockStatus.RELEASED.value,
        )
        .count()
        == 1
    )
    assert (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == second_intent.id,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        )
        .count()
        == 1
    )


def test_l4c_flag_off_release_is_no_op(db: Session, locks_off, monkeypatch):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)

    service_result = release_product_locks_for_intent(
        db, intent_id=bundle.intent.id, reason="test"
    )
    assert service_result.skipped is True
    assert service_result.released_count == 0

    orchestrator_result = release_orchestrator_product_locks_for_intent(
        db, bundle.intent, reason="test"
    )
    assert orchestrator_result.skipped is True
    assert orchestrator_result.reason == "product_locks_not_enabled_for_person"


def test_l4c_flag_off_settlement_worker_hooks_no_op(db: Session, monkeypatch, locks_off):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)
    bal_before, dep_before = _economic_counts(db, pe.person_id)

    created = process_transaction_outbox_intent_created(db)
    assert created["processed"] == 1

    db.refresh(bundle.intent)
    phase_before_settle = bundle.intent.current_phase
    settle_outbox = TransactionOutboxRepository.insert_event(
        db,
        intent_id=bundle.intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
        payload_json={"l4c_flag_off": True},
    )
    db.commit()

    settle = process_transaction_outbox_intent_settle(db)
    assert settle["processed"] == 1

    db.refresh(bundle.intent)
    db.refresh(settle_outbox)
    assert db.query(TransactionProductLock).count() == 0
    assert bundle.intent.current_phase == IntentOrchestratorPhase.SETTLED_NOOP.value
    assert phase_before_settle == IntentOrchestratorPhase.QUEUED.value
    assert settle_outbox.status == OutboxEventStatus.PROCESSED.value
    bal_after, dep_after = _economic_counts(db, pe.person_id)
    assert bal_after == bal_before
    assert dep_after == dep_before


def test_l4c_flag_off_worker_failed_intent_hook_no_op(db: Session, monkeypatch, locks_off):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)
    bundle.intent.status = IntentStatus.FAILED.value
    db.commit()

    handle_intent_created_event(db, bundle.outbox)

    assert db.query(TransactionProductLock).count() == 0


def test_l4c_flag_off_settle_terminal_failure_hook_no_op(db: Session, monkeypatch, locks_off):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)
    assert process_transaction_outbox_intent_created(db)["processed"] == 1
    bundle.intent.idempotency_key = "   "
    settle_outbox = TransactionOutboxRepository.insert_event(
        db,
        intent_id=bundle.intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
    )
    db.commit()
    bal_before, dep_before = _economic_counts(db, pe.person_id)

    result = process_transaction_outbox_intent_settle(db)
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    assert bundle.intent.status == IntentStatus.FAILED.value
    assert db.query(TransactionProductLock).count() == 0
    bal_after, dep_after = _economic_counts(db, pe.person_id)
    assert bal_after == bal_before
    assert dep_after == dep_before


def test_l4c_release_after_settlement_success(db: Session, monkeypatch, locks_on):
    pe, bundle, lock, settle_outbox = _seed_queued_with_lock(db, monkeypatch)
    bal_before, dep_before = _economic_counts(db, pe.person_id)

    result = process_transaction_outbox_intent_settle(db)
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    db.refresh(settle_outbox)
    released = (
        db.query(TransactionProductLock)
        .filter(TransactionProductLock.id == lock.id)
        .one()
    )
    assert released.status == ProductLockStatus.RELEASED.value
    assert released.released_at is not None
    assert bundle.intent.current_phase == IntentOrchestratorPhase.SETTLED_NOOP.value
    assert settle_outbox.status == OutboxEventStatus.PROCESSED.value

    bal_after, dep_after = _economic_counts(db, pe.person_id)
    assert bal_after == bal_before
    assert dep_after == dep_before


def test_l4c_release_after_ledger_settled(db: Session, monkeypatch, locks_on):
    pe, bundle, lock, settle_outbox = _seed_queued_with_lock_confirmed_swap(db, monkeypatch)
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")

    result = process_transaction_outbox_intent_settle(db)
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    assert bundle.intent.current_phase == IntentOrchestratorPhase.LEDGER_SETTLED.value

    released = (
        db.query(TransactionProductLock)
        .filter(TransactionProductLock.id == lock.id)
        .one()
    )
    assert released.status == ProductLockStatus.RELEASED.value


def test_l4c_release_after_terminal_failure(db: Session, monkeypatch, locks_on):
    pe, bundle, lock, settle_outbox = _seed_queued_with_lock(db, monkeypatch)
    bundle.intent.idempotency_key = "   "
    db.commit()

    result = process_transaction_outbox_intent_settle(db)
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    released = (
        db.query(TransactionProductLock)
        .filter(TransactionProductLock.id == lock.id)
        .one()
    )
    assert released.status == ProductLockStatus.RELEASED.value
    assert bundle.intent.status == IntentStatus.FAILED.value


def test_l4c_release_on_settle_dead_letter(db: Session, monkeypatch, locks_on):
    pe, bundle, lock, settle_outbox = _seed_queued_with_lock(db, monkeypatch)
    settle_outbox.max_attempts = 1
    settle_outbox.attempt_count = 0
    db.commit()

    def _boom(_db: Session, *, intent_id):
        raise RuntimeError("simulated_settle_dead_letter")

    monkeypatch.setattr(
        "services.transaction_outbox.settlement_worker.settle_transaction_intent_idempotently",
        _boom,
    )

    result = process_transaction_outbox_intent_settle(db)
    assert result["failed"] == 1

    db.refresh(settle_outbox)
    assert settle_outbox.status == OutboxEventStatus.DEAD_LETTER.value
    released = (
        db.query(TransactionProductLock)
        .filter(TransactionProductLock.id == lock.id)
        .one()
    )
    assert released.status == ProductLockStatus.RELEASED.value


def test_l4c_release_on_intent_failed_at_worker_start(db: Session, monkeypatch, locks_on):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)
    apply_orchestrator_product_locks_before_queued(db, bundle.intent)
    db.commit()

    assert (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == bundle.intent.id,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        )
        .count()
        == 1
    )

    bundle.intent.status = IntentStatus.FAILED.value
    db.commit()

    handle_intent_created_event(db, bundle.outbox)
    db.commit()

    assert (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == bundle.intent.id,
            TransactionProductLock.status == ProductLockStatus.RELEASED.value,
        )
        .count()
        == 1
    )


def test_l4c_orchestrator_release_skips_non_orchestrator_intent(db: Session, locks_on):
    pe = make_linked_client(db)
    intent = _intent(db, pe.person_id)
    db.commit()

    result = release_orchestrator_product_locks_for_intent(
        db, intent, reason="test"
    )
    assert result.skipped is True
    assert result.reason == "not_orchestrator_lifi"


def test_l4c_orchestrator_product_locks_has_no_forbidden_imports():
    root = (
        pathlib.Path(__file__).resolve().parents[1]
        / "services"
        / "transaction_outbox"
    )
    forbidden = ("services.settlement", "services.onchain_indexer.controller")
    source = (root / "orchestrator_product_locks.py").read_text()
    for token in forbidden:
        assert token not in source, f"orchestrator_product_locks.py must not reference {token}"
