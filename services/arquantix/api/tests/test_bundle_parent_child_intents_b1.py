"""B1 — modèle parent/child Bundle sur transaction_intents (migration 176)."""
from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.bundle_parent_child_repository import (
    bundle_child_idempotency_key,
    find_bundle_leg,
    find_by_bundle_execution_id,
    find_children,
    find_parent,
    is_bundle_child_intent,
    is_bundle_parent_intent,
)
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


pytestmark = pytest.mark.skipif(
    not _migration_176_ready(),
    reason="Migration 176 requise (transaction_intents parent/child B1).",
)


def _insert_parent(
    db: Session,
    *,
    person_id: uuid.UUID,
    bundle_execution_id: uuid.UUID,
    idempotency_key: str,
) -> TransactionIntent:
    row = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        operation_type=IntentOperationType.INVEST.value,
        idempotency_key=idempotency_key,
        status=IntentStatus.CREATED.value,
        intent_role=IntentRole.PARENT.value,
        bundle_execution_id=bundle_execution_id,
        linked_table="bundle_invest_lock",
        linked_reference_id=str(bundle_execution_id),
        metadata_json={"bundle_execution_group_id": str(bundle_execution_id)},
    )
    db.add(row)
    db.flush()
    return row


def _insert_child(
    db: Session,
    *,
    person_id: uuid.UUID,
    parent: TransactionIntent,
    leg_index: int,
    asset: str,
    idempotency_key: str | None = None,
) -> TransactionIntent:
    row = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_LEG.value,
        operation_type=IntentOperationType.BUNDLE_LEG.value,
        idempotency_key=idempotency_key
        or bundle_child_idempotency_key(
            parent_intent_id=parent.id,
            leg_index=leg_index,
        ),
        status=IntentStatus.CREATED.value,
        intent_role=IntentRole.CHILD.value,
        parent_intent_id=parent.id,
        leg_index=leg_index,
        bundle_execution_id=parent.bundle_execution_id,
        metadata_json={"target_asset": asset, "leg_index": leg_index},
    )
    db.add(row)
    db.flush()
    return row


def test_migration_176_columns_present():
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'transaction_intents'
                  AND column_name IN (
                      'parent_intent_id',
                      'intent_role',
                      'leg_index',
                      'bundle_execution_id'
                  )
                """
            )
        ).fetchall()
    assert {r[0] for r in rows} == {
        "parent_intent_id",
        "intent_role",
        "leg_index",
        "bundle_execution_id",
    }


def test_migration_176_parent_leg_index_unique_index():
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'uq_transaction_intents_parent_leg_index'
                """
            )
        ).fetchone()
    assert row is not None
    indexdef = row[0].lower()
    assert "unique" in indexdef
    assert "parent_intent_id" in indexdef
    assert "leg_index" in indexdef


def test_parent_with_three_children(db: Session):
    pe = make_linked_client(db)
    execution_id = uuid.uuid4()
    parent = _insert_parent(
        db,
        person_id=pe.person_id,
        bundle_execution_id=execution_id,
        idempotency_key=f"bundle_invest:{pe.person_id}:{execution_id}",
    )
    children = [
        _insert_child(db, person_id=pe.person_id, parent=parent, leg_index=i, asset=asset)
        for i, asset in enumerate(("CBBTC", "CBETH", "AAVE"))
    ]
    db.commit()

    assert is_bundle_parent_intent(parent)
    assert all(is_bundle_child_intent(c) for c in children)
    assert find_parent(db, intent_id=children[1].id) == parent
    found = find_children(db, parent_intent_id=parent.id)
    assert [c.leg_index for c in found] == [0, 1, 2]
    assert find_bundle_leg(db, parent_intent_id=parent.id, leg_index=2).id == children[2].id


def test_unique_leg_index_per_parent(db: Session):
    pe = make_linked_client(db)
    execution_id = uuid.uuid4()
    parent = _insert_parent(
        db,
        person_id=pe.person_id,
        bundle_execution_id=execution_id,
        idempotency_key=f"bundle_invest:{pe.person_id}:{execution_id}:dup",
    )
    _insert_child(db, person_id=pe.person_id, parent=parent, leg_index=0, asset="ETH")
    with pytest.raises(IntegrityError):
        _insert_child(
            db,
            person_id=pe.person_id,
            parent=parent,
            leg_index=0,
            asset="ETH",
            idempotency_key=f"bundle_leg:dup-test:{parent.id}:0:b",
        )
    db.rollback()


def test_standalone_lifi_intent_without_parent_valid(db: Session):
    pe = make_linked_client(db)
    standalone = TransactionIntent(
        person_id=pe.person_id,
        product_type=IntentProductType.LIFI_SWAP.value,
        operation_type=IntentOperationType.SWAP.value,
        idempotency_key=f"lifi-swap:test:{uuid.uuid4()}",
        status=IntentStatus.CREATED.value,
    )
    db.add(standalone)
    db.commit()

    assert standalone.parent_intent_id is None
    assert standalone.intent_role is None
    assert standalone.leg_index is None
    assert standalone.bundle_execution_id is None
    assert find_parent(db, intent_id=standalone.id) is None
    assert find_children(db, parent_intent_id=standalone.id) == []


def test_find_by_bundle_execution_id(db: Session):
    pe = make_linked_client(db)
    execution_id = uuid.uuid4()
    parent = _insert_parent(
        db,
        person_id=pe.person_id,
        bundle_execution_id=execution_id,
        idempotency_key=f"bundle_invest:{pe.person_id}:{execution_id}:group",
    )
    _insert_child(db, person_id=pe.person_id, parent=parent, leg_index=0, asset="UNI")
    db.commit()

    all_rows = find_by_bundle_execution_id(db, bundle_execution_id=execution_id)
    assert len(all_rows) == 2
    parents = find_by_bundle_execution_id(
        db,
        bundle_execution_id=execution_id,
        intent_role=IntentRole.PARENT,
    )
    assert len(parents) == 1
    assert parents[0].id == parent.id


def test_bundle_child_idempotency_key_format():
    parent_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    assert bundle_child_idempotency_key(parent_intent_id=parent_id, leg_index=2) == (
        f"bundle_leg:{parent_id}:2"
    )


def test_migration_176_revision_chain():
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/176_transaction_intents_bundle_parent_child_b1.py"
    )
    text = path.read_text(encoding="utf-8")
    assert 'revision = "176"' in text
    assert 'down_revision = "175"' in text
    assert "def upgrade()" in text
    assert "def downgrade()" in text


def test_no_settlement_worker_controller_imports():
    """B1 helpers ne doivent pas importer settlement / worker / controller."""
    import services.transaction_intents.bundle_parent_child_repository as mod

    source_path = mod.__file__
    assert source_path is not None
    text = open(source_path, encoding="utf-8").read().lower()
    forbidden = (
        "settlement",
        "transaction_outbox",
        "controller",
        "product_locks",
        "apply_swap_settlement",
    )
    for token in forbidden:
        assert token not in text, f"unexpected import reference: {token}"
