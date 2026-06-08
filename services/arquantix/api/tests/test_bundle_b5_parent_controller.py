"""B5 — Bundle parent controller minimal (proof aggregator)."""
from __future__ import annotations

import inspect
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.event_driven import bundle_parent_controller as b5_module
from services.portfolio_engine.bundles.event_driven.bundle_child_factory import (
    PHASE_CHILD_LEGS_CREATED,
)
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_CHILD_REPORT_KEY,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
    BUNDLE_LEG_SETTLEMENT_RECEIPT_KEY,
    compute_child_report_hash,
)
from services.portfolio_engine.bundles.event_driven.bundle_parent_controller import (
    PHASE_RECONCILED,
    BundleParentControllerError,
    compute_parent_report_hash,
    reconcile_bundle_parent_idempotently,
)
from services.portfolio_engine.positions.models import PositionAtom
from services.transaction_intents.bundle_parent_child_repository import bundle_child_idempotency_key
from services.transaction_intents.enums import (
    IntentOperationType,
    IntentProductType,
    IntentRole,
    IntentStatus,
)
from tests.conftest import make_linked_client


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

PLAN_HASH = "sha256:plan-test-b5"
PLANNER_VERSION = "v1"
SETTLEMENT_RECEIPT = "sha256:settlement-receipt-b5-test"

FORBIDDEN_SOURCE_TOKENS = (
    "settle_bundle",
    "apply_rebalance",
    "release_global_user_transaction_lock",
    "release_bundle_parent_lock",
    "PersonWalletSwap",
    "apply_swap_settlement",
    "PositionAtom",
)


def _frozen_plan_leg(*, leg_index: int = 0, notional_usdc: str = "1") -> dict:
    return {
        "leg_index": leg_index,
        "direction": "buy",
        "from_asset": "USDC",
        "to_asset": "AAVE",
        "from_chain": "base",
        "to_chain": "base",
        "notional_usdc": notional_usdc,
    }


def _insert_parent(
    db: Session,
    *,
    person_id: uuid.UUID,
    phase: str = PHASE_CHILD_LEGS_CREATED,
    plan_hash: str = PLAN_HASH,
    legs: list[dict] | None = None,
) -> TransactionIntent:
    plan_legs = legs if legs is not None else [_frozen_plan_leg()]
    parent = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        operation_type=IntentOperationType.INVEST.value,
        intent_role=IntentRole.PARENT.value,
        status=IntentStatus.CREATED.value,
        metadata_json={
            "phase": phase,
            "plan_hash": plan_hash,
            "planner_version": PLANNER_VERSION,
            "rebalance_plan_after_funding": {"legs": plan_legs},
        },
    )
    db.add(parent)
    db.flush()
    return parent


def _child_report_hash(child_id: uuid.UUID, *, leg_index: int = 0) -> str:
    return compute_child_report_hash(
        child_intent_id=child_id,
        settlement_receipt_hash=SETTLEMENT_RECEIPT,
        plan_hash=PLAN_HASH,
        planner_version=PLANNER_VERSION,
        leg_index=leg_index,
    )


def _insert_settled_child(
    db: Session,
    *,
    person_id: uuid.UUID,
    parent_id: uuid.UUID,
    leg_index: int = 0,
    plan_hash: str = PLAN_HASH,
    planner_version: str = PLANNER_VERSION,
    include_receipt: bool = True,
    include_child_report: bool = True,
) -> TransactionIntent:
    child_id = uuid.uuid4()
    child_report = _child_report_hash(child_id, leg_index=leg_index) if include_child_report else ""
    settlement_block: dict = {
        "phase": BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
        "settled": True,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "leg_index": leg_index,
    }
    if include_receipt:
        settlement_block[BUNDLE_LEG_SETTLEMENT_RECEIPT_KEY] = SETTLEMENT_RECEIPT
    if include_child_report:
        settlement_block[BUNDLE_LEG_CHILD_REPORT_KEY] = child_report

    child = TransactionIntent(
        id=child_id,
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_LEG.value,
        operation_type=IntentOperationType.INVEST.value,
        intent_role=IntentRole.CHILD.value,
        parent_intent_id=parent_id,
        leg_index=leg_index,
        status=IntentStatus.CREATED.value,
        idempotency_key=bundle_child_idempotency_key(
            parent_intent_id=parent_id,
            leg_index=leg_index,
        ),
        metadata_json={
            "plan_hash": plan_hash,
            "planner_version": planner_version,
            BUNDLE_LEG_SETTLEMENT_BLOCK_KEY: settlement_block,
        },
    )
    db.add(child)
    db.flush()
    return child


@pytest.fixture
def parent_controller_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_PARENT_CONTROLLER_ENABLED", "true")


def test_module_has_no_forbidden_economic_imports():
    source = inspect.getsource(b5_module)
    for token in FORBIDDEN_SOURCE_TOKENS:
        assert token not in source


def test_compute_parent_report_hash_stable_and_includes_receipts():
    parent_id = uuid.uuid4()
    proofs = [
        (0, "sha256:child-a", "sha256:receipt-a"),
        (1, "sha256:child-b", "sha256:receipt-b"),
    ]
    first = compute_parent_report_hash(
        parent_intent_id=parent_id,
        plan_hash=PLAN_HASH,
        planner_version=PLANNER_VERSION,
        expected_leg_count=2,
        child_proofs=proofs,
    )
    second = compute_parent_report_hash(
        parent_intent_id=parent_id,
        plan_hash=PLAN_HASH,
        planner_version=PLANNER_VERSION,
        expected_leg_count=2,
        child_proofs=list(reversed(proofs)),
    )
    assert first == second
    assert first.startswith("sha256:")


def test_reconcile_disabled_is_strict_noop(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)
    db.commit()
    before = dict(parent.metadata_json or {})

    result = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    db.refresh(parent)

    assert result.skipped is True
    assert result.reconciled is False
    assert result.reason == "disabled"
    assert parent.metadata_json == before


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_single_child_sets_parent_reconciled(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    child = _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)
    pe_before = db.query(PositionAtom).count()

    result = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    db.commit()
    db.refresh(parent)
    pe_after = db.query(PositionAtom).count()

    assert result.reconciled is True
    assert result.idempotent is False
    assert result.parent_report_hash is not None
    assert parent.metadata_json["phase"] == PHASE_RECONCILED
    assert parent.metadata_json["parent_report_hash"] == result.parent_report_hash
    block = parent.metadata_json["bundle_parent_controller"]
    assert block["expected_leg_count"] == 1
    assert block["child_proofs"][0]["settlement_receipt_hash"] == SETTLEMENT_RECEIPT
    assert block["child_proofs"][0]["child_report_hash"] == _child_report_hash(child.id)
    assert pe_before == pe_after


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_idempotent_second_run(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)

    first = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    db.commit()
    meta_after_first = dict(parent.metadata_json or {})
    second = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    db.commit()
    db.refresh(parent)

    assert first.parent_report_hash == second.parent_report_hash
    assert second.idempotent is True
    assert second.reason == "parent_already_reconciled"
    assert parent.metadata_json == meta_after_first


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_child_not_settled_is_retryable(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    child = TransactionIntent(
        person_id=client.person_id,
        product_type=IntentProductType.BUNDLE_LEG.value,
        operation_type=IntentOperationType.INVEST.value,
        intent_role=IntentRole.CHILD.value,
        parent_intent_id=parent.id,
        leg_index=0,
        status=IntentStatus.CREATED.value,
        idempotency_key=bundle_child_idempotency_key(
            parent_intent_id=parent.id,
            leg_index=0,
        ),
        metadata_json={"status": "awaiting_swap"},
    )
    db.add(child)
    db.flush()

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.child_not_settled"
    assert exc.value.retryable is True


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_missing_child_is_retryable(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(
        db,
        person_id=client.person_id,
        legs=[_frozen_plan_leg(leg_index=0), _frozen_plan_leg(leg_index=1, notional_usdc="2")],
    )
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id, leg_index=0)

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.child_missing"
    assert exc.value.retryable is True


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_plan_hash_mismatch_is_terminal(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(
        db,
        person_id=client.person_id,
        parent_id=parent.id,
        plan_hash="sha256:other-plan",
    )

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.plan_hash_mismatch"
    assert exc.value.retryable is False


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_missing_child_report_hash_is_retryable(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(
        db,
        person_id=client.person_id,
        parent_id=parent.id,
        include_child_report=False,
    )

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.missing_child_report_hash"
    assert exc.value.retryable is True


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_missing_settlement_receipt_hash_is_retryable(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(
        db,
        person_id=client.person_id,
        parent_id=parent.id,
        include_receipt=False,
    )

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.missing_settlement_receipt_hash"
    assert exc.value.retryable is True


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_duplicate_leg_index_is_terminal(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id, leg_index=0)
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id, leg_index=0)

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.duplicate_child_leg"
    assert exc.value.retryable is False


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_parent_completed_raises(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id, phase="COMPLETED")
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.parent_completed"
    assert exc.value.retryable is False
