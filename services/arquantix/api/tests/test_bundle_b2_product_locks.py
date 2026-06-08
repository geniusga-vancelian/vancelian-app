"""B2 — Product Lock parent Bundle (flag + allowlist · legacy lock intact)."""
from __future__ import annotations

import inspect
import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_invest_lock import BUNDLE_INVEST_LOCK_KEY
from services.portfolio_engine.bundles.event_driven.bundle_product_locks import (
    BUNDLE_PARENT_LOCK_ASSET,
    acquire_bundle_parent_lock,
    build_bundle_parent_snapshot,
    build_bundle_parent_snapshot_if_enabled,
    release_bundle_parent_lock,
)
from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.portfolio_engine.portfolios.models import Portfolio
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import ProductLockConflict
from services.product_locks.models import TransactionProductLock
from services.product_locks.service import acquire_product_lock
from services.transaction_intents.enums import IntentProductType, IntentRole
from tests.conftest import make_linked_client
from tests.product_locks_test_utils import enable_product_locks_allowlist
from tests.test_product_locks_l2_engine import _migration_175_ready


def _migration_176_ready() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'transaction_intents'
                      AND column_name = 'parent_intent_id'
                    """
                )
            ).fetchone()
            return row is not None
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _migration_175_ready(), reason="Migration 175 requise."),
    pytest.mark.skipif(not _migration_176_ready(), reason="Migration 176 requise."),
]


PLANNED = [
    {"asset": "CBBTC", "weight_bps": 4000, "planned_usdc": "40"},
    {"asset": "CBETH", "weight_bps": 3500, "planned_usdc": "35"},
    {"asset": "AAVE", "weight_bps": 2500, "planned_usdc": "25"},
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


def _pe_snapshot(pe_client) -> CurrentPeScopeSnapshot:
    snap = CurrentPeScopeSnapshot(
        person_id=pe_client.person_id,
        client_id=pe_client.id,
    )
    snap.trading_available = {"USDC": Decimal("200")}
    snap.bundle_cash = {"USDC": Decimal("10")}
    snap.bundle_position = {"ETH": Decimal("0.5"), "AAVE": Decimal("1")}
    return snap


def _parent_intent(db: Session, person_id: uuid.UUID) -> TransactionIntent:
    execution_id = uuid.uuid4()
    row = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        operation_type="invest",
        idempotency_key=f"bundle_invest:test:{uuid.uuid4()}",
        status="created",
        intent_role=IntentRole.PARENT.value,
        bundle_execution_id=execution_id,
        linked_table="bundle_invest_lock",
        linked_reference_id=str(execution_id),
    )
    db.add(row)
    db.flush()
    return row


def _bundle_portfolio(db: Session, pe_client) -> Portfolio:
    row = Portfolio(
        client_id=pe_client.id,
        portfolio_type="bundle_portfolio",
        name="Test Bundle Portfolio",
        status="active",
        metadata_={
            BUNDLE_INVEST_LOCK_KEY: {
                "batch_id": str(uuid.uuid4()),
                "status": "pending_signature",
            }
        },
    )
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def locks_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")


@pytest.fixture
def locks_off(monkeypatch):
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", raising=False)
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", raising=False)


def test_flag_off_acquire_is_no_op(db: Session, locks_off):
    pe = make_linked_client(db)
    wallet = _wallet(db, pe)
    parent = _parent_intent(db, pe.person_id)

    result = acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
    )

    assert result.skipped is True
    assert result.acquired is False
    assert result.lock is None
    assert result.snapshot is None
    assert db.query(TransactionProductLock).count() == 0


def test_flag_on_allowlist_creates_bundle_scope_lock(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="bundle-b2-pilot@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    parent = _parent_intent(db, pe.person_id)

    result = acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    assert result.skipped is False
    assert result.acquired is True
    assert result.lock is not None
    assert result.lock.scope == ProductLockScope.BUNDLE.value
    assert result.lock.asset == BUNDLE_PARENT_LOCK_ASSET
    assert result.lock.product_type == IntentProductType.BUNDLE_INVEST.value
    assert result.lock.intent_id == parent.id
    assert result.snapshot is not None
    assert result.snapshot.funding["amount_usdc"] == "100"
    assert "trading_available" in result.snapshot.scopes
    assert "bundle_cash" in result.snapshot.scopes
    assert "bundle_position" in result.snapshot.scopes
    assert len(result.snapshot.planned_allocations) == 3


def test_same_parent_intent_is_idempotent(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="bundle-b2-idem@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    parent = _parent_intent(db, pe.person_id)

    first = acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
    )
    second = acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
    )
    db.commit()

    assert first.acquired is True
    assert second.idempotent is True
    assert db.query(TransactionProductLock).filter(
        TransactionProductLock.intent_id == parent.id,
        TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
    ).count() == 1


def test_second_parent_same_wallet_bundle_scope_conflicts(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="bundle-b2-conflict@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    parent_a = _parent_intent(db, pe.person_id)
    parent_b = _parent_intent(db, pe.person_id)
    pe_snap = _pe_snapshot(pe)

    acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent_a.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=pe_snap,
    )
    db.flush()

    with pytest.raises(ProductLockConflict):
        acquire_bundle_parent_lock(
            db,
            person_id=pe.person_id,
            wallet_id=wallet.id,
            parent_intent_id=parent_b.id,
            funding_amount_usdc=Decimal("100"),
            planned_allocations=PLANNED,
            pe_snapshot=pe_snap,
        )


def test_trading_available_lock_distinct_from_bundle_scope(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="bundle-b2-scopes@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    swap_intent = TransactionIntent(
        person_id=pe.person_id,
        product_type="lifi_swap",
        operation_type="swap",
        idempotency_key=f"lifi-swap:lock-test:{uuid.uuid4()}",
        status="created",
    )
    db.add(swap_intent)
    db.flush()
    parent = _parent_intent(db, pe.person_id)

    trading = acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset=BUNDLE_PARENT_LOCK_ASSET,
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=swap_intent.id,
    )
    bundle = acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
    )
    db.commit()

    assert trading.acquired is True
    assert bundle.acquired is True
    assert (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.person_id == pe.person_id,
            TransactionProductLock.wallet_id == wallet.id,
            TransactionProductLock.asset == BUNDLE_PARENT_LOCK_ASSET,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        )
        .count()
        == 2
    )


def test_snapshot_contains_required_fields(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="bundle-b2-snap@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    execution_id = uuid.uuid4()

    result = build_bundle_parent_snapshot_if_enabled(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        bundle_execution_id=execution_id,
        execution_buffer_usdc=Decimal("1"),
    )

    assert result.skipped is False
    snap = result.snapshot
    assert snap is not None
    assert snap.scopes["trading_available"]["USDC"] == "200"
    assert snap.scopes["bundle_cash"]["USDC"] == "10"
    assert snap.scopes["bundle_position"]["ETH"] == "0.5"
    assert snap.planned_allocations[0]["asset"] == "AAVE"
    assert snap.execution_buffer_usdc == "1"
    assert snap.balance_snapshot_hash.startswith("sha256:")


def test_release_bundle_parent_lock(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="bundle-b2-release@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    parent = _parent_intent(db, pe.person_id)

    acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
    )
    released = release_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
    )
    db.commit()

    assert released.released is True
    lock = (
        db.query(TransactionProductLock)
        .filter(TransactionProductLock.intent_id == parent.id)
        .one()
    )
    assert lock.status == ProductLockStatus.RELEASED.value
    assert lock.released_at is not None


def test_legacy_bundle_invest_lock_metadata_unchanged(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="bundle-b2-legacy@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    portfolio = _bundle_portfolio(db, pe)
    parent = _parent_intent(db, pe.person_id)
    before = dict(portfolio.metadata_ or {})

    acquire_bundle_parent_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
    )
    db.refresh(portfolio)

    assert portfolio.metadata_ == before
    assert BUNDLE_INVEST_LOCK_KEY in (portfolio.metadata_ or {})


def test_build_snapshot_pure_without_db_gate():
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_available = {"USDC": Decimal("50")}
    result = build_bundle_parent_snapshot(
        person_id=pe.person_id,
        wallet_id=uuid.uuid4(),
        funding_amount_usdc=Decimal("50"),
        planned_allocations=PLANNED,
        pe_snapshot=pe,
    )
    assert result.skipped is False
    assert result.snapshot is not None


def test_no_settlement_worker_controller_imports():
    import services.portfolio_engine.bundles.event_driven.bundle_product_locks as mod

    text = inspect.getsource(mod).lower()
    for token in ("settlement", "transaction_outbox", "controller", "apply_swap_settlement"):
        assert token not in text, token
