"""B5 — Bundle parent controller minimal (proof aggregator)."""
from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.event_driven.bundle_child_factory import (
    PHASE_CHILD_LEGS_CREATED,
    PHASE_REBALANCE_PLAN_FROZEN,
)
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_CHILD_REPORT_KEY,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
    compute_child_report_hash,
)
from services.portfolio_engine.bundles.event_driven.bundle_parent_controller import (
    PHASE_RECONCILED,
    BundleParentControllerError,
    compute_parent_report_hash,
    reconcile_bundle_parent_idempotently,
)
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
) -> TransactionIntent:
    child_id = uuid.uuid4()
    child_report = _child_report_hash(child_id, leg_index=leg_index)
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
            "planner_version": PLANNER_VERSION,
            BUNDLE_LEG_SETTLEMENT_BLOCK_KEY: {
                "phase": BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
                "settled": True,
                "plan_hash": plan_hash,
                "planner_version": PLANNER_VERSION,
                "leg_index": leg_index,
                BUNDLE_LEG_CHILD_REPORT_KEY: child_report,
            },
        },
    )
    db.add(child)
    db.flush()
    return child


@pytest.fixture
def parent_controller_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_PARENT_CONTROLLER_ENABLED", "true")


def test_compute_parent_report_hash_stable():
    parent_id = uuid.uuid4()
    child_reports = [(0, "sha256:child-a"), (1, "sha256:child-b")]
    first = compute_parent_report_hash(
        parent_intent_id=parent_id,
        plan_hash=PLAN_HASH,
        planner_version=PLANNER_VERSION,
        child_reports=child_reports,
    )
    second = compute_parent_report_hash(
        parent_intent_id=parent_id,
        plan_hash=PLAN_HASH,
        planner_version=PLANNER_VERSION,
        child_reports=list(reversed(child_reports)),
    )
    assert first == second
    assert first.startswith("sha256:")


def test_reconcile_disabled_raises(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)
    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.disabled"


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_single_child_sets_parent_reconciled(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    child = _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)

    result = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    db.commit()
    db.refresh(parent)

    assert result.reconciled is True
    assert result.idempotent is False
    assert result.parent_report_hash is not None
    assert len(result.child_report_hashes) == 1
    assert parent.metadata_json["phase"] == PHASE_RECONCILED
    assert parent.metadata_json["parent_report_hash"] == result.parent_report_hash
    block = parent.metadata_json["bundle_parent_reconciliation"]
    assert block["plan_hash"] == PLAN_HASH
    assert block["child_report_hashes"][0]["leg_index"] == 0
    assert block["child_report_hashes"][0]["child_report_hash"] == _child_report_hash(child.id)


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_idempotent_second_run(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id)
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)

    first = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    db.commit()
    second = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    db.commit()

    assert first.parent_report_hash == second.parent_report_hash
    assert second.idempotent is True
    assert second.reason == "parent_already_reconciled"


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_child_not_settled_raises(db: Session):
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


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_missing_child_raises(db: Session):
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


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_plan_hash_mismatch_raises(db: Session):
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


@pytest.mark.usefixtures("parent_controller_on")
def test_reconcile_parent_completed_raises(db: Session):
    client = make_linked_client(db)
    parent = _insert_parent(db, person_id=client.person_id, phase="COMPLETED")
    _insert_settled_child(db, person_id=client.person_id, parent_id=parent.id)

    with pytest.raises(BundleParentControllerError) as exc:
        reconcile_bundle_parent_idempotently(db, parent_intent_id=parent.id)
    assert exc.value.code == "bundle.parent_controller.parent_completed"
