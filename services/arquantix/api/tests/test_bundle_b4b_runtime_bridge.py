"""B4b — Bundle minimal runtime bridge (parent FROZEN → lock → swap → settle B3c)."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_funding import sum_bundle_cash_leg_quantity
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import is_bundle_internal_swap
from services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge import (
    CHILD_STATUS_SWAP_ATTACHED,
    BundleB4bBridgeError,
    run_bundle_b4b_minimal_bridge,
)
from services.portfolio_engine.bundles.event_driven.bundle_child_factory import (
    B4A_CHAIN,
    B4A_FROM_ASSET,
    B4A_TO_ASSET,
    CHILD_STATUS_AWAITING_SWAP,
    PHASE_CHILD_LEGS_CREATED,
    PHASE_REBALANCE_PLAN_FROZEN,
    create_bundle_child_intents_from_frozen_plan,
)
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
)
from services.product_locks.enums import ProductLockStatus
from services.product_locks.exceptions import TransactionInProgress409
from services.product_locks.global_user_transaction_lock import (
    acquire_global_user_transaction_lock,
    find_active_global_user_transaction_lock,
)
from services.product_locks.models import TransactionProductLock
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.transaction_intents.bundle_parent_child_repository import find_bundle_leg, find_children
from services.transaction_intents.enums import (
    IntentOperationType,
    IntentProductType,
    IntentRole,
    IntentStatus,
)
from tests.conftest import make_linked_client
from tests.test_bundle_b4a_bundle_child_factory import (
    NOTIONAL,
    PLANNER_VERSION,
    PLAN_HASH,
    _frozen_plan_leg,
    _insert_frozen_parent,
)
from tests.test_bundle_b3c_bundle_leg_settlement_handler import _instrument_aave, _seed_bundle_cash
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc, _seed_privy_usdc
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


pytestmark_db = pytest.mark.skipif(
    not (_migration_175_ready() and _migration_176_ready()),
    reason="Migrations 175+176 requises (locks + parent/child).",
)

EVM_ADDR = f"0x{uuid.uuid4().hex[:40]}"


@pytest.fixture
def b4b_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", "true")
    monkeypatch.setenv("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED", "true")


@pytest.fixture
def b4b_off(monkeypatch):
    monkeypatch.delenv("BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED", raising=False)


def _wallet(db: Session, pe):
    return upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=EVM_ADDR,
    )


def _setup_parent_rail(db: Session, *, phase: str = PHASE_REBALANCE_PLAN_FROZEN):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    aave = _instrument_aave(db)
    portfolio = _bundle_portfolio(db, pe.id)
    wallet = _wallet(db, pe)
    _seed_privy_usdc(db, pe.person_id, wallet.id, "1000")
    _seed_bundle_cash(db, portfolio.id, usdc.id, "200")
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        phase=phase,
    )
    db.commit()
    return pe, usdc, aave, portfolio, wallet, parent


def _make_swap(
    db: Session,
    *,
    person_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    parent_id: uuid.UUID,
    child_id: uuid.UUID,
    status: str = SwapSessionStatus.QUOTE_RECEIVED.value,
    with_bundle_context: bool = True,
) -> PersonWalletSwap:
    swap_id = uuid.uuid4()
    audit: list[dict] = [{"event": "bundle_quote_requested", "bundle_execution": True}]
    if with_bundle_context:
        audit.append(
            {
                "event": "bundle_leg_context",
                "bundle_execution": True,
                "batch_id": str(parent_id),
                "leg_id": "leg-0",
                "leg_index": 0,
                "portfolio_id": str(portfolio_id),
                "bundle_action": "invest",
                "leg_action": "rebalance_buy",
                "parent_intent_id": str(parent_id),
                "child_intent_id": str(child_id),
                "plan_hash": PLAN_HASH,
                "planner_version": PLANNER_VERSION,
            }
        )
    swap = PersonWalletSwap(
        id=swap_id,
        person_id=person_id,
        status=status,
        from_asset=B4A_FROM_ASSET,
        to_asset=B4A_TO_ASSET,
        from_chain=B4A_CHAIN,
        to_chain=B4A_CHAIN,
        amount_in=Decimal(NOTIONAL),
        estimated_receive=Decimal("0.5"),
        audit_log=audit,
    )
    if status == SwapSessionStatus.CONFIRMED.value:
        swap.tx_hash = f"0x{uuid.uuid4().hex}"
        swap.confirmed_at = datetime.now(timezone.utc)
    db.add(swap)
    db.flush()
    return swap


def _mock_fresh_swap(monkeypatch, db: Session, *, status: str):
    created: list[PersonWalletSwap] = []

    def _fake_create(db_sess, **kwargs):
        swap = _make_swap(
            db_sess,
            person_id=kwargs["person_id"],
            portfolio_id=kwargs["portfolio_id"],
            parent_id=kwargs["parent_intent_id"],
            child_id=kwargs["child_intent_id"],
            status=status,
        )
        created.append(swap)
        return swap

    monkeypatch.setattr(
        "services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge._create_fresh_bundle_swap",
        _fake_create,
    )
    return created


def _count_swaps(db: Session) -> int:
    return int(db.execute(sa.text("SELECT COUNT(*) FROM person_wallet_swaps")).scalar())


def _count_pe_atoms(db: Session) -> int:
    try:
        return int(db.execute(sa.text("SELECT COUNT(*) FROM position_atoms")).scalar())
    except Exception:
        pytest.skip("Table position_atoms absente")


def _count_cb_executions(db: Session) -> int:
    try:
        return int(db.execute(sa.text("SELECT COUNT(*) FROM cost_basis_executions")).scalar())
    except Exception:
        pytest.skip("Table cost_basis_executions absente")


def _count_legs(db: Session) -> int:
    try:
        return int(db.execute(sa.text("SELECT COUNT(*) FROM bundle_cash_legs")).scalar())
    except Exception:
        pytest.skip("Table bundle_cash_legs absente")


@pytestmark_db
def test_flag_off_strict_no_op(db: Session, b4b_off):
    pe, usdc, _aave, portfolio, _wallet, parent = _setup_parent_rail(db)
    swaps_before = _count_swaps(db)
    pe_before = _count_pe_atoms(db)

    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)

    assert result.skipped is True
    assert result.reason == "bundle_b4b_runtime_bridge_disabled"
    assert _count_swaps(db) == swaps_before
    assert _count_pe_atoms(db) == pe_before
    assert find_bundle_leg(db, parent_intent_id=parent.id, leg_index=0) is None
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None


@pytestmark_db
def test_parent_frozen_creates_child(db: Session, b4b_on, monkeypatch):
    pe, _usdc, _aave, _portfolio, _wallet, parent = _setup_parent_rail(db)
    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.QUOTE_RECEIVED.value)

    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    child = find_bundle_leg(db, parent_intent_id=parent.id, leg_index=0)
    assert child is not None
    assert result.child_intent_id == child.id
    assert child.metadata_json.get("status") == CHILD_STATUS_AWAITING_SWAP
    assert len(find_children(db, parent_intent_id=parent.id)) == 1
    db.refresh(parent)
    assert parent.metadata_json.get("phase") == PHASE_CHILD_LEGS_CREATED


@pytestmark_db
def test_child_existing_reused(db: Session, b4b_on, monkeypatch):
    pe, _usdc, _aave, portfolio, _wallet, parent = _setup_parent_rail(db)
    factory = create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    child_id = factory.child_intent_id
    db.commit()

    created = _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.QUOTE_RECEIVED.value)
    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    assert result.child_intent_id == child_id
    assert len(created) == 1
    assert len(find_children(db, parent_intent_id=parent.id)) == 1


@pytestmark_db
def test_global_lock_conflict_409(db: Session, b4b_on, monkeypatch):
    pe, _usdc, _aave, _portfolio, _wallet, parent = _setup_parent_rail(db)
    other_intent = TransactionIntent(
        person_id=pe.person_id,
        product_type="lifi_swap",
        operation_type="swap",
        idempotency_key=f"b4b-lock-blocker-{uuid.uuid4().hex}",
        status=IntentStatus.CREATED.value,
    )
    db.add(other_intent)
    db.flush()
    acquire_global_user_transaction_lock(
        db,
        person_id=pe.person_id,
        intent_id=other_intent.id,
        reason="blocker",
    )
    db.commit()

    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.QUOTE_RECEIVED.value)

    with pytest.raises(TransactionInProgress409) as exc_info:
        run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)

    assert exc_info.value.error_code == "transaction_in_progress"


@pytestmark_db
def test_fresh_swap_created_and_tagged_bundle_execution(db: Session, b4b_on, monkeypatch):
    _pe, _usdc, _aave, _portfolio, _wallet, parent = _setup_parent_rail(db)
    created = _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.QUOTE_RECEIVED.value)

    run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    swap = created[0]
    assert is_bundle_internal_swap(swap) is True
    audit = swap.audit_log or []
    ctx_events = [
        e for e in audit if isinstance(e, dict) and e.get("event") == "bundle_leg_context"
    ]
    assert ctx_events
    ctx = ctx_events[-1]
    assert ctx.get("bundle_execution") is True
    assert ctx.get("parent_intent_id")
    assert ctx.get("child_intent_id")
    assert ctx.get("leg_index") == 0


@pytestmark_db
def test_swap_attached_to_child(db: Session, b4b_on, monkeypatch):
    _pe, _usdc, _aave, _portfolio, _wallet, parent = _setup_parent_rail(db)
    created = _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.QUOTE_RECEIVED.value)

    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    child = db.get(TransactionIntent, result.child_intent_id)
    assert child.linked_table == "person_wallet_swaps"
    assert child.linked_id == created[0].id
    meta = child.metadata_json
    assert meta.get("entry_instrument_id")
    assert meta.get("target_instrument_id")
    assert meta.get("planned_amount_in") == NOTIONAL
    assert meta.get("status") == "swap_attached"


@pytestmark_db
def test_missing_confirmed_no_settlement(db: Session, b4b_on, monkeypatch):
    pe, usdc, _aave, portfolio, _wallet, parent = _setup_parent_rail(db)
    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.QUOTE_RECEIVED.value)

    cash_before = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)
    pe_before = _count_pe_atoms(db)

    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    assert result.awaiting_swap_confirmation is True
    assert result.settled is False
    assert result.global_lock_released is False
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is not None
    assert sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id) == cash_before
    assert _count_pe_atoms(db) == pe_before

    child = db.get(TransactionIntent, result.child_intent_id)
    assert (child.metadata_json or {}).get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY) is None


@pytestmark_db
def test_confirmed_settles_child(db: Session, b4b_on, monkeypatch):
    pe, usdc, aave, portfolio, _wallet, parent = _setup_parent_rail(db)
    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.CONFIRMED.value)

    cash_before = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)
    pe_before = _count_pe_atoms(db)

    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    assert result.settled is True
    assert result.global_lock_released is True
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None

    child = db.get(TransactionIntent, result.child_intent_id)
    settlement = (child.metadata_json or {}).get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY) or {}
    assert settlement.get("settled") is True
    assert settlement.get("phase") == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED
    assert sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id) < cash_before
    assert _count_pe_atoms(db) > pe_before


@pytestmark_db
def test_idempotent_second_run_no_economic_change(db: Session, b4b_on, monkeypatch):
    pe, usdc, _aave, portfolio, _wallet, parent = _setup_parent_rail(db)
    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.CONFIRMED.value)

    first = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    swaps_after_first = _count_swaps(db)
    pe_after_first = _count_pe_atoms(db)
    cash_after_first = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)
    cb_after_first = _count_cb_executions(db)
    legs_after_first = _count_legs(db)

    second = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    assert first.settled is True
    assert second.idempotent is True
    assert second.settled is True
    assert second.reason == "child_already_ledger_settled"
    assert _count_swaps(db) == swaps_after_first
    assert _count_pe_atoms(db) == pe_after_first
    assert sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id) == cash_after_first
    assert _count_cb_executions(db) == cb_after_first
    assert _count_legs(db) == legs_after_first
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None


@pytestmark_db
def test_release_global_lock_on_success(db: Session, b4b_on, monkeypatch):
    pe, _usdc, _aave, _portfolio, _wallet, parent = _setup_parent_rail(db)
    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.CONFIRMED.value)

    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    assert result.global_lock_released is True
    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None
    released = (
        db.query(TransactionProductLock)
        .filter(
            TransactionProductLock.intent_id == parent.id,
            TransactionProductLock.status == ProductLockStatus.RELEASED.value,
        )
        .first()
    )
    assert released is not None


@pytestmark_db
def test_release_global_lock_on_failure(db: Session, b4b_on, monkeypatch):
    pe, _usdc, _aave, _portfolio, _wallet, parent = _setup_parent_rail(db)
    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.CONFIRMED.value)

    def _boom(*_args, **_kwargs):
        raise BundleB4bBridgeError("bundle.b4b.test_failure", "forced failure")

    monkeypatch.setattr(
        "services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge.settle_bundle_leg_idempotently",
        _boom,
    )

    with pytest.raises(BundleB4bBridgeError):
        run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    assert find_active_global_user_transaction_lock(db, person_id=pe.person_id) is None


@pytestmark_db
def test_no_parent_reconciled_or_completed(db: Session, b4b_on, monkeypatch):
    _pe, _usdc, _aave, _portfolio, _wallet, parent = _setup_parent_rail(db)
    parent_meta_before = dict(parent.metadata_json or {})
    _mock_fresh_swap(monkeypatch, db, status=SwapSessionStatus.CONFIRMED.value)

    run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    db.refresh(parent)
    meta = parent.metadata_json or {}
    assert meta.get("phase") not in {"RECONCILED", "COMPLETED"}
    assert parent.status not in {"reconciled", "completed", "RECONCILED", "COMPLETED"}
    for forbidden in ("finalize", "controller_parent", "reconciled_at", "completed_at"):
        assert forbidden not in meta
    assert meta.get("plan_hash") == parent_meta_before.get("plan_hash")


@pytestmark_db
def test_no_n_legs_rejected(db: Session, b4b_on):
    pe, _usdc, _aave, portfolio, _wallet, parent = _setup_parent_rail(
        db,
        phase=PHASE_REBALANCE_PLAN_FROZEN,
    )
    meta = dict(parent.metadata_json or {})
    meta["rebalance_plan_after_funding"] = {
        "legs": [_frozen_plan_leg(leg_index=0), _frozen_plan_leg(leg_index=1)],
    }
    parent.metadata_json = meta
    db.add(parent)
    db.commit()

    with pytest.raises(Exception) as exc_info:
        run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)

    assert "multiple" in str(exc_info.value).lower() or "1" in str(exc_info.value)


@pytestmark_db
def test_no_sell_rejected(db: Session, b4b_on):
    pe, _usdc, _aave, portfolio, _wallet, parent = _setup_parent_rail(db)
    meta = dict(parent.metadata_json or {})
    meta["rebalance_plan_after_funding"] = {
        "legs": [_frozen_plan_leg(direction="sell")],
    }
    parent.metadata_json = meta
    db.add(parent)
    db.commit()

    with pytest.raises(Exception) as exc_info:
        run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)

    assert "sell" in str(exc_info.value).lower()


def test_no_controller_imports():
    import services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge as mod

    source = inspect.getsource(mod)
    assert "bundle_controller" not in source
    assert "BundleController" not in source
    assert "finalize_bundle" not in source


@pytestmark_db
def test_swap_not_recreated_when_already_attached(db: Session, b4b_on, monkeypatch):
    pe, usdc, aave, portfolio, _wallet, parent = _setup_parent_rail(db)
    factory = create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    child = db.get(TransactionIntent, factory.child_intent_id)
    swap = _make_swap(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        parent_id=parent.id,
        child_id=child.id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
    )
    child.linked_table = "person_wallet_swaps"
    child.linked_id = swap.id
    db.add(child)
    db.commit()

    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("fresh swap should not be created when already attached")

    monkeypatch.setattr(
        "services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge._create_fresh_bundle_swap",
        _should_not_run,
    )

    result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent.id)
    db.commit()

    assert result.swap_id == swap.id
    assert result.awaiting_swap_confirmation is True
