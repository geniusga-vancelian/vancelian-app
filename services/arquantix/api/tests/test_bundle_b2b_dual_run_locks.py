"""B2b — Dual-run locks Bundle (legacy metadata + S4 parent · failure paths)."""
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
from services.portfolio_engine.bundles.bundle_invest_lock import (
    BUNDLE_INVEST_LOCK_KEY,
    acquire_invest_lock,
    get_invest_lock,
)
from services.portfolio_engine.bundles.event_driven.bundle_dual_run_locks import (
    release_bundle_dual_run_locks,
    try_acquire_s4_after_legacy_invest_lock,
)
from services.portfolio_engine.bundles.event_driven.bundle_product_locks import (
    BUNDLE_PARENT_LOCK_ASSET,
    acquire_bundle_parent_lock,
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
    snap.bundle_position = {"ETH": Decimal("0.5")}
    return snap


def _portfolio(db: Session, pe_client) -> Portfolio:
    row = Portfolio(
        client_id=pe_client.id,
        portfolio_type="bundle_portfolio",
        name="B2b Dual Run Portfolio",
        status="active",
        metadata_={},
    )
    db.add(row)
    db.flush()
    return row


def _parent_intent(db: Session, person_id: uuid.UUID) -> TransactionIntent:
    execution_id = uuid.uuid4()
    row = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        operation_type="invest",
        idempotency_key=f"bundle_invest:b2b:{uuid.uuid4()}",
        status="created",
        intent_role=IntentRole.PARENT.value,
        bundle_execution_id=execution_id,
        linked_table="bundle_invest_lock",
        linked_reference_id=str(execution_id),
    )
    db.add(row)
    db.flush()
    return row


def _acquire_legacy(
    db: Session,
    *,
    portfolio: Portfolio,
    pe_client,
    batch_id: str,
    funding_amount: str = "100",
) -> dict:
    return acquire_invest_lock(
        db,
        portfolio,
        client_id=pe_client.id,
        batch_id=batch_id,
        status="pending_signature",
        funding_asset="USDC",
        funding_amount=funding_amount,
    )


@pytest.fixture
def dual_run_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED", "true")


@pytest.fixture
def dual_run_off(monkeypatch):
    monkeypatch.delenv("BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED", raising=False)


@pytest.fixture
def locks_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")


@pytest.fixture
def locks_off(monkeypatch):
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", raising=False)
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", raising=False)


def test_dual_run_flag_off_no_s4_lock_legacy_unchanged(
    db: Session, dual_run_off, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-off@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)
    wallet = _wallet(db, pe)

    result = try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        wallet_id=wallet.id,
    )
    db.commit()

    assert result.dual_run_flag_on is False
    assert result.s4_attempted is False
    assert result.skip_reason == "dual_run_flag_off"
    assert db.query(TransactionProductLock).count() == 0
    assert get_invest_lock(portfolio.metadata_) is not None
    assert get_invest_lock(portfolio.metadata_)["batch_id"] == batch_id
    db.refresh(parent)
    assert parent.metadata_json.get("bundle_parent_snapshot") is None
    assert parent.metadata_json.get("dual_run_s4_active") is None


def test_dual_run_on_creates_legacy_and_s4_lock(
    db: Session, dual_run_on, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-on@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)
    wallet = _wallet(db, pe)

    result = try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        wallet_id=wallet.id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    assert result.s4_acquired is True
    assert get_invest_lock(portfolio.metadata_) is not None
    s4 = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == parent.id,
            TransactionProductLock.scope == ProductLockScope.BUNDLE.value,
        )
        .one()
    )
    assert s4.status == ProductLockStatus.ACTIVE.value
    db.refresh(parent)
    assert parent.metadata_json.get("bundle_parent_snapshot") is not None
    assert parent.metadata_json.get("dual_run_s4_active") is True


def test_s4_failure_rolls_back_legacy_lock(
    db: Session, dual_run_on, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-rollback@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
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
        try_acquire_s4_after_legacy_invest_lock(
            db,
            person_id=pe.person_id,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            portfolio=portfolio,
            batch_id=batch_id,
            parent_intent_id=parent_b.id,
            funding_amount_usdc=Decimal("100"),
            planned_allocations=PLANNED,
            pe_snapshot=pe_snap,
            wallet_id=wallet.id,
        )
    db.refresh(portfolio)

    assert get_invest_lock(portfolio.metadata_) is None
    lock_meta = (portfolio.metadata_ or {}).get(BUNDLE_INVEST_LOCK_KEY)
    assert lock_meta is not None
    assert lock_meta["status"] == "failed"


def test_release_success_clears_legacy_and_s4(
    db: Session, dual_run_on, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-release@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)
    wallet = _wallet(db, pe)

    try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        wallet_id=wallet.id,
    )
    released = release_bundle_dual_run_locks(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        wallet_id=wallet.id,
        legacy_terminal="clear",
    )
    db.commit()

    assert released.s4_released is True
    assert released.legacy_cleared is True
    assert get_invest_lock(portfolio.metadata_) is None
    s4 = db.query(TransactionProductLock).filter(TransactionProductLock.intent_id == parent.id).one()
    assert s4.status == ProductLockStatus.RELEASED.value


def test_same_parent_s4_idempotent(
    db: Session, dual_run_on, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-idem@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)
    wallet = _wallet(db, pe)
    pe_snap = _pe_snapshot(pe)
    kwargs = dict(
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=pe_snap,
        wallet_id=wallet.id,
    )

    first = try_acquire_s4_after_legacy_invest_lock(db, **kwargs)
    second = try_acquire_s4_after_legacy_invest_lock(db, **kwargs)
    db.commit()

    assert first.s4_acquired is True
    assert second.s4_idempotent is True
    assert (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == parent.id,
            TransactionProductLock.status == ProductLockStatus.ACTIVE.value,
        )
        .count()
        == 1
    )


def test_second_bundle_same_wallet_usdc_bundle_conflict(
    db: Session, dual_run_on, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-conflict@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    pe_snap = _pe_snapshot(pe)

    portfolio_a = _portfolio(db, pe)
    batch_a = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio_a, pe_client=pe, batch_id=batch_a)
    parent_a = _parent_intent(db, pe.person_id)
    try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio_a.id,
        portfolio=portfolio_a,
        batch_id=batch_a,
        parent_intent_id=parent_a.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=pe_snap,
        wallet_id=wallet.id,
    )
    db.flush()

    portfolio_b = _portfolio(db, pe)
    batch_b = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio_b, pe_client=pe, batch_id=batch_b)
    parent_b = _parent_intent(db, pe.person_id)

    with pytest.raises(ProductLockConflict):
        try_acquire_s4_after_legacy_invest_lock(
            db,
            person_id=pe.person_id,
            client_id=pe.id,
            portfolio_id=portfolio_b.id,
            portfolio=portfolio_b,
            batch_id=batch_b,
            parent_intent_id=parent_b.id,
            funding_amount_usdc=Decimal("100"),
            planned_allocations=PLANNED,
            pe_snapshot=pe_snap,
            wallet_id=wallet.id,
        )
    db.refresh(portfolio_b)
    assert get_invest_lock(portfolio_b.metadata_) is None


def test_product_locks_off_s4_noop_legacy_only(
    db: Session, dual_run_on, locks_off,
):
    pe = make_linked_client(db, email="b2b-pl-off@example.com")
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)
    wallet = _wallet(db, pe)

    result = try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        wallet_id=wallet.id,
    )
    db.commit()

    assert result.s4_skipped is True
    assert result.skip_reason == "product_locks_not_enabled_for_person"
    assert db.query(TransactionProductLock).count() == 0
    assert get_invest_lock(portfolio.metadata_) is not None


def test_hors_allowlist_s4_noop_legacy_only(
    db: Session, dual_run_on, locks_on,
):
    pe = make_linked_client(db, email="b2b-not-allowlisted@example.com")
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)
    wallet = _wallet(db, pe)

    result = try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        wallet_id=wallet.id,
    )
    db.commit()

    assert result.s4_skipped is True
    assert db.query(TransactionProductLock).count() == 0
    assert get_invest_lock(portfolio.metadata_) is not None


def test_trading_available_distinct_from_bundle_dual_run(
    db: Session, dual_run_on, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-scopes@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    wallet = _wallet(db, pe)
    swap_intent = TransactionIntent(
        person_id=pe.person_id,
        product_type="lifi_swap",
        operation_type="swap",
        idempotency_key=f"lifi-swap:b2b:{uuid.uuid4()}",
        status="created",
    )
    db.add(swap_intent)
    db.flush()

    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset=BUNDLE_PARENT_LOCK_ASSET,
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=swap_intent.id,
    )

    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)

    result = try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        wallet_id=wallet.id,
    )
    db.commit()

    assert result.s4_acquired is True
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


def test_release_s4_idempotent_second_call(
    db: Session, dual_run_on, locks_on, monkeypatch,
):
    pe = make_linked_client(db, email="b2b-rel-idem@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    portfolio = _portfolio(db, pe)
    batch_id = str(uuid.uuid4())
    _acquire_legacy(db, portfolio=portfolio, pe_client=pe, batch_id=batch_id)
    parent = _parent_intent(db, pe.person_id)
    wallet = _wallet(db, pe)

    try_acquire_s4_after_legacy_invest_lock(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=portfolio,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        funding_amount_usdc=Decimal("100"),
        planned_allocations=PLANNED,
        pe_snapshot=_pe_snapshot(pe),
        wallet_id=wallet.id,
    )
    first = release_bundle_dual_run_locks(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        wallet_id=wallet.id,
        legacy_terminal="keep",
    )
    second = release_bundle_dual_run_locks(
        db,
        person_id=pe.person_id,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        parent_intent_id=parent.id,
        wallet_id=wallet.id,
        legacy_terminal="keep",
    )
    db.commit()

    assert first.s4_released is True
    assert second.s4_idempotent is True


def test_no_settlement_worker_controller_imports():
    import services.portfolio_engine.bundles.event_driven.bundle_dual_run_locks as mod

    text = inspect.getsource(mod).lower()
    for token in ("settlement", "transaction_outbox", "controller", "apply_swap_settlement"):
        assert token not in text, token
