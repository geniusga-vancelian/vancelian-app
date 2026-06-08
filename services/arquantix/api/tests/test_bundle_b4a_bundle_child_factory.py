"""B4a — Bundle child factory (parent FROZEN → child #0 auto · no swap · no settlement)."""
from __future__ import annotations

import inspect
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_funding import sum_bundle_cash_leg_quantity
from services.portfolio_engine.bundles.event_driven.bundle_child_factory import (
    B4A_CHAIN,
    B4A_DIRECTION_BUY,
    B4A_FROM_ASSET,
    B4A_LEG_INDEX,
    B4A_TO_ASSET,
    CHILD_STATUS_AWAITING_SWAP,
    PHASE_CHILD_LEGS_CREATED,
    PHASE_REBALANCE_PLAN_FROZEN,
    BundleChildFactoryError,
    create_bundle_child_intents_from_frozen_plan,
)
from services.transaction_intents.bundle_parent_child_repository import (
    bundle_child_idempotency_key,
    find_bundle_leg,
    find_children,
)
from services.transaction_intents.enums import (
    IntentOperationType,
    IntentProductType,
    IntentRole,
    IntentStatus,
)
from tests.conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


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
    not _migration_176_ready(),
    reason="Migration 176 requise (transaction_intents parent/child B1).",
)

PLAN_HASH = "sha256:plan-test-b4a"
PLANNER_VERSION = "v1"
NOTIONAL = "50"


def _frozen_plan_leg(
    *,
    leg_index: int = B4A_LEG_INDEX,
    direction: str = B4A_DIRECTION_BUY,
    from_asset: str = B4A_FROM_ASSET,
    to_asset: str = B4A_TO_ASSET,
    from_chain: str = B4A_CHAIN,
    to_chain: str = B4A_CHAIN,
    notional_usdc: str = NOTIONAL,
) -> dict:
    return {
        "leg_index": leg_index,
        "direction": direction,
        "from_asset": from_asset,
        "to_asset": to_asset,
        "from_chain": from_chain,
        "to_chain": to_chain,
        "notional_usdc": notional_usdc,
    }


def _insert_frozen_parent(
    db: Session,
    *,
    person_id: uuid.UUID,
    portfolio_id: uuid.UUID | None = None,
    bundle_execution_id: uuid.UUID | None = None,
    phase: str = PHASE_REBALANCE_PLAN_FROZEN,
    plan_hash: str = PLAN_HASH,
    planner_version: str = PLANNER_VERSION,
    legs: list[dict] | None = None,
    metadata_extra: dict | None = None,
) -> TransactionIntent:
    bex = bundle_execution_id or uuid.uuid4()
    plan_legs = legs if legs is not None else [_frozen_plan_leg()]
    meta: dict = {
        "bundle_execution_group_id": str(bex),
        "phase": phase,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "rebalance_plan_after_funding": {"legs": plan_legs},
    }
    if portfolio_id is not None:
        meta["portfolio_id"] = str(portfolio_id)
    if metadata_extra:
        meta.update(metadata_extra)

    row = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        operation_type=IntentOperationType.INVEST.value,
        idempotency_key=f"bundle-b4a-parent-{uuid.uuid4().hex}",
        status=IntentStatus.CREATED.value,
        intent_role=IntentRole.PARENT.value,
        bundle_execution_id=bex,
        linked_table="bundle_invest_lock",
        linked_reference_id=str(bex),
        metadata_json=meta,
    )
    db.add(row)
    db.flush()
    return row


def _setup_parent(db: Session) -> tuple[uuid.UUID, uuid.UUID, TransactionIntent]:
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(db, person_id=pe.person_id, portfolio_id=portfolio.id)
    db.commit()
    return pe.person_id, portfolio.id, parent


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


@pytestmark_db
def test_frozen_parent_creates_child_leg_zero(db: Session):
    _, _, parent = _setup_parent(db)

    result = create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    db.commit()

    assert result.created is True
    assert result.idempotent is False
    assert result.child_intent_id is not None
    assert result.leg_index == B4A_LEG_INDEX
    assert result.plan_hash == PLAN_HASH
    assert result.planner_version == PLANNER_VERSION

    child = find_bundle_leg(db, parent_intent_id=parent.id, leg_index=B4A_LEG_INDEX)
    assert child is not None
    assert child.product_type == IntentProductType.BUNDLE_LEG.value
    assert child.intent_role == IntentRole.CHILD.value
    assert child.parent_intent_id == parent.id
    assert child.bundle_execution_id == parent.bundle_execution_id
    assert child.idempotency_key == bundle_child_idempotency_key(
        parent_intent_id=parent.id,
        leg_index=B4A_LEG_INDEX,
    )


@pytestmark_db
def test_child_metadata_contains_planner_triplet(db: Session):
    _, _, parent = _setup_parent(db)

    result = create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    db.commit()

    child = db.get(TransactionIntent, result.child_intent_id)
    meta = child.metadata_json or {}
    assert meta["planner_version"] == PLANNER_VERSION
    assert meta["plan_hash"] == PLAN_HASH
    assert meta["leg_index"] == B4A_LEG_INDEX
    assert meta["leg_direction"] == B4A_DIRECTION_BUY
    assert meta["from_asset"] == B4A_FROM_ASSET
    assert meta["to_asset"] == B4A_TO_ASSET
    assert meta["from_chain"] == B4A_CHAIN
    assert meta["to_chain"] == B4A_CHAIN
    assert meta["notional_usdc"] == NOTIONAL
    assert meta["status"] == CHILD_STATUS_AWAITING_SWAP


@pytestmark_db
def test_parent_child_triplet_coherent(db: Session):
    _, portfolio_id, parent = _setup_parent(db)

    create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    db.commit()

    db.refresh(parent)
    parent_meta = parent.metadata_json or {}
    assert parent_meta["phase"] == PHASE_CHILD_LEGS_CREATED
    assert parent_meta["plan_hash"] == PLAN_HASH
    assert parent_meta["planner_version"] == PLANNER_VERSION

    child_ids = parent_meta.get("child_intent_ids") or []
    assert len(child_ids) == 1

    child = db.get(TransactionIntent, uuid.UUID(child_ids[0]))
    child_meta = child.metadata_json or {}
    assert child_meta["plan_hash"] == parent_meta["plan_hash"]
    assert child_meta["planner_version"] == parent_meta["planner_version"]
    assert child_meta["portfolio_id"] == str(portfolio_id)


@pytestmark_db
def test_second_call_idempotent(db: Session):
    _, _, parent = _setup_parent(db)

    first = create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    db.commit()
    children_after_first = find_children(db, parent_intent_id=parent.id)

    second = create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    db.commit()
    children_after_second = find_children(db, parent_intent_id=parent.id)

    assert first.created is True
    assert second.created is False
    assert second.idempotent is True
    assert second.reason == "child_leg_already_exists"
    assert second.child_intent_id == first.child_intent_id
    assert len(children_after_first) == 1
    assert len(children_after_second) == 1


@pytestmark_db
def test_parent_not_frozen_rejected(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        phase="FUNDED",
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.parent_not_frozen"


@pytestmark_db
def test_missing_plan_hash_rejected(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        plan_hash="",
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.missing_plan_hash"


@pytestmark_db
def test_missing_planner_version_rejected(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        planner_version="",
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.missing_planner_version"


@pytestmark_db
def test_empty_plan_rejected(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        legs=[],
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.empty_plan"


@pytestmark_db
def test_multiple_legs_rejected_b4a_v1(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        legs=[_frozen_plan_leg(), _frozen_plan_leg(leg_index=1)],
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.multiple_legs_not_allowed_b4a"


@pytestmark_db
def test_non_aave_asset_rejected_b4a_v1(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        legs=[_frozen_plan_leg(to_asset="UNI")],
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.invalid_asset_pair_b4a"


@pytestmark_db
def test_non_base_chain_rejected_b4a_v1(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        legs=[_frozen_plan_leg(from_chain="ethereum", to_chain="ethereum")],
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.chain_not_base_b4a"


@pytestmark_db
def test_sell_direction_rejected_b4a_v1(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    parent = _insert_frozen_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        legs=[_frozen_plan_leg(direction="sell", from_asset="AAVE", to_asset="USDC")],
    )
    db.commit()

    with pytest.raises(BundleChildFactoryError) as exc:
        create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.child_factory.sell_not_allowed_b4a"


@pytestmark_db
def test_no_pe_cb_legs_change(db: Session):
    _, portfolio_id, parent = _setup_parent(db)
    usdc = _instrument_usdc(db)

    pe_before = _count_pe_atoms(db)
    cb_before = _count_cb_executions(db)
    cash_before = sum_bundle_cash_leg_quantity(db, portfolio_id, usdc.id)

    create_bundle_child_intents_from_frozen_plan(db, parent_intent_id=parent.id)
    db.commit()

    pe_after = _count_pe_atoms(db)
    cb_after = _count_cb_executions(db)
    cash_after = sum_bundle_cash_leg_quantity(db, portfolio_id, usdc.id)

    assert pe_after == pe_before
    assert cb_after == cb_before
    assert cash_after == cash_before


def test_api_accepts_parent_intent_id_only():
    sig = inspect.signature(create_bundle_child_intents_from_frozen_plan)
    params = [p for p in sig.parameters if p != "db"]
    assert params == ["parent_intent_id"]


def test_no_settlement_worker_controller_imports_in_factory_source():
    import services.portfolio_engine.bundles.event_driven.bundle_child_factory as mod

    text = inspect.getsource(mod).lower()
    forbidden = (
        "bundle_leg_settlement_handler",
        "settle_bundle_leg",
        "lifi",
        "transaction_outbox",
        "settlement_worker",
        "lifi_swap_controller",
        "reconcile_lifi_swap",
        "services.settlement.settle",
        "person_wallet_swaps",
        "linked_id",
    )
    for token in forbidden:
        assert token not in text, token
