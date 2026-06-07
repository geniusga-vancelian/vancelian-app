"""S4 L4b — runtime wiring product locks sur worker intent.created (flag OFF par défaut)."""
from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.product_locks.balance_snapshot import BalanceSnapshot, compute_balance_snapshot_hash
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import BalanceChanged409, ProductLockConflict409
from services.product_locks.models import TransactionProductLock
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.orchestrator_product_locks import (
    BALANCE_SNAPSHOT_VERSION,
    apply_orchestrator_product_locks_before_queued,
)
from services.transaction_outbox.worker import process_transaction_outbox_intent_created
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.product_locks_test_utils import enable_product_locks_allowlist
from tests.test_product_locks_l2_engine import _migration_175_ready
from tests.test_transaction_outbox_worker_s2b import _economic_counts, _migration_173_ready


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


def test_l4b_flag_off_worker_behavior_unchanged(db: Session, monkeypatch, locks_off):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)
    bal_before, dep_before = _economic_counts(db, pe.person_id)

    result = process_transaction_outbox_intent_created(db)
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    assert bundle.intent.current_phase == IntentOrchestratorPhase.QUEUED.value
    assert (bundle.intent.metadata_json or {}).get("balance_snapshot") is None
    assert db.query(TransactionProductLock).count() == 0

    bal_after, dep_after = _economic_counts(db, pe.person_id)
    assert bal_after == bal_before
    assert dep_after == dep_before


def test_l4b_flag_on_worker_creates_snapshot_and_lock(db: Session, monkeypatch, locks_on):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)

    result = process_transaction_outbox_intent_created(db)
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    snapshot = (bundle.intent.metadata_json or {}).get("balance_snapshot")
    assert snapshot is not None
    assert snapshot["asset"] == "USDC"
    assert "hash" in snapshot

    lock = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == bundle.intent.id,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        )
        .one()
    )
    assert lock.asset == "USDC"
    assert lock.scope == ProductLockScope.TRADING_AVAILABLE.value


def test_l4b_flag_on_second_intent_same_slot_conflict(db: Session, monkeypatch, locks_on):
    pe, first = _seed_orchestrator_intent(db, monkeypatch)
    first_result = process_transaction_outbox_intent_created(db)
    assert first_result["processed"] == 1

    second = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
    )
    db.commit()

    second_result = process_transaction_outbox_intent_created(db)
    assert second_result["processed"] == 0
    assert second_result["failed"] == 0
    assert second_result["deferred_same_scope"] == 1

    db.refresh(second.intent)
    assert second.intent.current_phase == IntentOrchestratorPhase.CREATED.value
    assert (second.intent.metadata_json or {}).get("balance_snapshot") is None
    assert db.query(TransactionProductLock).count() == 1


def test_l4b_flag_on_different_asset_allowed(db: Session, monkeypatch, locks_on):
    pe, first = _seed_orchestrator_intent(db, monkeypatch)
    assert process_transaction_outbox_intent_created(db)["processed"] == 1

    second = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="EURC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("5"),
    )
    db.commit()

    second_result = process_transaction_outbox_intent_created(db)
    assert second_result["processed"] == 1
    assert db.query(TransactionProductLock).count() == 2


def test_l4b_lock_conflict_does_not_write_ledger(db: Session, monkeypatch, locks_on):
    pe, first = _seed_orchestrator_intent(db, monkeypatch)
    bal_before, dep_before = _economic_counts(db, pe.person_id)
    assert process_transaction_outbox_intent_created(db)["processed"] == 1

    second = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("3"),
    )
    db.commit()

    process_transaction_outbox_intent_created(db)
    bal_after, dep_after = _economic_counts(db, pe.person_id)
    assert bal_after == bal_before
    assert dep_after == dep_before


def test_l4b_existing_snapshot_mismatch_raises(db: Session, monkeypatch, locks_on):
    pe, bundle = _seed_orchestrator_intent(db, monkeypatch)
    wallet = _wallet(db, pe)
    stale = BalanceSnapshot(
        asset="USDC",
        available="100",
        version=BALANCE_SNAPSHOT_VERSION,
        hash=compute_balance_snapshot_hash(
            person_id=pe.person_id,
            wallet_id=wallet.id,
            asset="USDC",
            scope=ProductLockScope.TRADING_AVAILABLE,
            available="100",
            version=BALANCE_SNAPSHOT_VERSION,
        ),
    )
    meta = dict(bundle.intent.metadata_json or {})
    meta["balance_snapshot"] = stale.to_dict()
    bundle.intent.metadata_json = meta
    db.commit()

    with pytest.raises(BalanceChanged409):
        apply_orchestrator_product_locks_before_queued(db, bundle.intent)


def test_l4b_apply_maps_acquire_conflict_to_409(db: Session, monkeypatch, locks_on):
    pe, first = _seed_orchestrator_intent(db, monkeypatch)
    apply_orchestrator_product_locks_before_queued(db, first.intent)
    db.commit()

    second = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
    )
    db.commit()

    with pytest.raises(ProductLockConflict409):
        apply_orchestrator_product_locks_before_queued(db, second.intent)


def test_l4b_orchestrator_product_locks_has_no_forbidden_imports():
    root = (
        pathlib.Path(__file__).resolve().parents[1]
        / "services"
        / "transaction_outbox"
    )
    forbidden = ("services.settlement", "services.onchain_indexer.controller")
    source = (root / "orchestrator_product_locks.py").read_text()
    for token in forbidden:
        assert token not in source, f"orchestrator_product_locks.py must not reference {token}"
