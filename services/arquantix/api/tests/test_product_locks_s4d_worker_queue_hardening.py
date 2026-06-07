"""S4d — worker queue hardening (séquentiel par lock_key)."""
from __future__ import annotations

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
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.lock_key import build_lock_key
from services.product_locks.models import TransactionProductLock
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.settlement_worker import process_transaction_outbox_intent_settle
from services.transaction_outbox.worker import process_transaction_outbox_intent_created
from services.transaction_outbox.worker_queue_hardening import resolve_orchestrator_intent_lock_key
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.product_locks_test_utils import enable_product_locks_allowlist
from tests.test_product_locks_l2_engine import _migration_175_ready
from tests.test_transaction_outbox_worker_s2b import _economic_counts, _migration_173_ready


EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


pytestmark = [
    pytest.mark.skipif(not _migration_173_ready(), reason="Migration 173 requise."),
    pytest.mark.skipif(not _migration_175_ready(), reason="Migration 175 requise."),
]


@pytest.fixture
def s4d_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")


def _wallet(db: Session, pe_client):
    link_external_identity_to_person(
        db,
        person_id=pe_client.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"did:privy:s4d-{uuid.uuid4().hex[:8]}",
        external_email=getattr(pe_client, "email", None) or "s4d@test.local",
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
        metadata_json={"privy_wallet_id": "w-s4d"},
    )


def _confirm_swap(db: Session, pe, bundle, *, to_asset: str, receive: str):
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="100",
            chain_id=8453,
        ),
    )
    bundle.swap.status = SwapSessionStatus.CONFIRMED.value
    bundle.swap.tx_hash = f"0x{uuid.uuid4().hex}"
    bundle.swap.estimated_receive = Decimal(receive)
    bundle.swap.confirmed_at = datetime.now(timezone.utc)
    bundle.swap.audit_log = [{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}]
    bundle.intent.assets_json = {
        "from": {"asset": bundle.swap.from_asset, "amount": str(bundle.swap.amount_in)},
        "to": {"asset": to_asset, "amount": receive},
    }


def _active_lock_count(db: Session) -> int:
    return (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
            TransactionProductLock.released_at.is_(None),
        )
        .count()
    )


def _dead_letter_count(db: Session) -> int:
    return db.execute(
        sa.text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")
    ).scalar()


def _run_tick_cycle(db: Session) -> tuple[dict, dict]:
    created = process_transaction_outbox_intent_created(db)
    settle = process_transaction_outbox_intent_settle(db)
    return created, settle


def test_s4d_batch_defers_duplicate_usdc_scope(db: Session, monkeypatch, s4d_on):
    pe = make_linked_client(db, email="s4d-batch@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    enable_product_locks_allowlist(monkeypatch, pe)
    _wallet(db, pe)
    bundles = [
        persist_intent_swap_outbox_atomic(
            db,
            person_id=pe.person_id,
            from_asset="USDC",
            to_asset="ETH",
            from_chain="base",
            to_chain="base",
            amount_in=Decimal("1"),
        )
        for _ in range(3)
    ]
    db.commit()

    result = process_transaction_outbox_intent_created(db)
    assert result["processed"] == 1
    assert result["deferred_same_scope"] == 2
    assert result["failed"] == 0
    assert _active_lock_count(db) == 1

    for bundle in bundles:
        db.refresh(bundle.intent)
    queued = sum(
        1 for b in bundles if b.intent.current_phase == IntentOrchestratorPhase.QUEUED.value
    )
    not_queued = sum(
        1
        for b in bundles
        if b.intent.current_phase
        in (IntentOrchestratorPhase.CREATED.value, IntentOrchestratorPhase.VALIDATED.value)
    )
    assert queued == 1
    assert not_queued == 2


def test_s4d_sequential_ticks_drain_three_usdc_intents(db: Session, monkeypatch, s4d_on):
    pe = make_linked_client(db, email="s4d-seq@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    enable_product_locks_allowlist(monkeypatch, pe)
    _wallet(db, pe)
    bundles = []
    for _ in range(3):
        bundle = persist_intent_swap_outbox_atomic(
            db,
            person_id=pe.person_id,
            from_asset="USDC",
            to_asset="UNI",
            from_chain="base",
            to_chain="base",
            amount_in=Decimal("1"),
        )
        _confirm_swap(db, pe, bundle, to_asset="UNI", receive="0.4")
        bundles.append(bundle)
    db.commit()

    pe_before, cb_before = _global_pe_cb(db)

    expected_deferred = [2, 1, 0]
    for tick, expected in enumerate(expected_deferred):
        created, settle = _run_tick_cycle(db)
        assert created["processed"] == 1
        assert created["deferred_same_scope"] == expected
        assert created["failed"] == 0
        assert settle["failed"] == 0
        assert _active_lock_count(db) == 0
        assert _dead_letter_count(db) == 0

    for bundle in bundles:
        db.refresh(bundle.intent)
        assert bundle.intent.current_phase == IntentOrchestratorPhase.LEDGER_SETTLED.value
        assert (bundle.intent.metadata_json or {}).get("balance_snapshot") is not None

    released = (
        db.query(TransactionProductLock)
        .filter(TransactionProductLock.status == ProductLockStatus.RELEASED.value)
        .count()
    )
    assert released == 3

    pe_after, cb_after = _global_pe_cb(db)
    assert pe_after == pe_before
    assert cb_after == cb_before


def _global_pe_cb(db: Session) -> tuple[int, int]:
    pe = db.execute(sa.text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
    cb = db.execute(sa.text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    return pe, cb


def test_s4d_different_assets_processed_in_parallel(db: Session, monkeypatch, s4d_on):
    pe = make_linked_client(db, email="s4d-parallel@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    usdc1 = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
    )
    persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="UNI",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("2"),
    )
    eth1 = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="ETH",
        to_asset="USDC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("0.001"),
    )
    db.commit()

    key_usdc = resolve_orchestrator_intent_lock_key(db, usdc1.intent)
    key_eth = resolve_orchestrator_intent_lock_key(db, eth1.intent)
    assert key_usdc is not None and key_eth is not None
    assert key_usdc != key_eth

    result = process_transaction_outbox_intent_created(db)
    assert result["processed"] == 2
    assert result["deferred_same_scope"] == 1
    assert _active_lock_count(db) == 2

    key_trading = build_lock_key(
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )
    key_bundle = build_lock_key(
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.BUNDLE,
    )
    assert key_trading != key_bundle


def test_s4d_lock_key_scopes_are_distinct():
    person_id = uuid.uuid4()
    wallet_id = uuid.uuid4()
    trading = build_lock_key(
        person_id=person_id,
        wallet_id=wallet_id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )
    bundle = build_lock_key(
        person_id=person_id,
        wallet_id=wallet_id,
        asset="USDC",
        scope=ProductLockScope.BUNDLE,
    )
    assert trading != bundle
