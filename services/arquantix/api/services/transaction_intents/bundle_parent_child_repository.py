"""B1 — helpers lecture parent/child Bundle sur transaction_intents.

Aucun wiring runtime : pas de création automatique de child intents en prod.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent

from .enums import IntentProductType, IntentRole


def bundle_child_idempotency_key(*, parent_intent_id: UUID, leg_index: int) -> str:
    """Clé idempotente canonique pour un child intent bundle leg (B1)."""
    return f"bundle_leg:{parent_intent_id}:{leg_index}"


def find_children(
    db: Session,
    *,
    parent_intent_id: UUID,
) -> list[TransactionIntent]:
    """Enfants ordonnés par leg_index (lecture seule)."""
    return (
        db.query(TransactionIntent)
        .filter(TransactionIntent.parent_intent_id == parent_intent_id)
        .order_by(TransactionIntent.leg_index.asc().nulls_last(), TransactionIntent.created_at.asc())
        .all()
    )


def find_parent(
    db: Session,
    *,
    intent_id: UUID,
) -> TransactionIntent | None:
    """Parent d'un intent enfant ; None si standalone ou parent absent."""
    row = db.get(TransactionIntent, intent_id)
    if row is None or row.parent_intent_id is None:
        return None
    return db.get(TransactionIntent, row.parent_intent_id)


def find_bundle_leg(
    db: Session,
    *,
    parent_intent_id: UUID,
    leg_index: int,
) -> TransactionIntent | None:
    """Child intent pour un leg_index donné sous un parent."""
    return (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.parent_intent_id == parent_intent_id,
            TransactionIntent.leg_index == leg_index,
        )
        .first()
    )


def find_by_bundle_execution_id(
    db: Session,
    *,
    bundle_execution_id: UUID,
    intent_role: IntentRole | str | None = None,
) -> list[TransactionIntent]:
    """Intents liés à un bundle_execution_id (parent + children)."""
    q = db.query(TransactionIntent).filter(
        TransactionIntent.bundle_execution_id == bundle_execution_id
    )
    if intent_role is not None:
        role = intent_role.value if isinstance(intent_role, IntentRole) else str(intent_role)
        q = q.filter(TransactionIntent.intent_role == role)
    return q.order_by(
        TransactionIntent.intent_role.asc().nulls_last(),
        TransactionIntent.leg_index.asc().nulls_last(),
        TransactionIntent.created_at.asc(),
    ).all()


def is_bundle_parent_intent(row: TransactionIntent) -> bool:
    return (
        row.product_type == IntentProductType.BUNDLE_INVEST.value
        and row.intent_role == IntentRole.PARENT.value
    )


def is_bundle_child_intent(row: TransactionIntent) -> bool:
    return (
        row.product_type == IntentProductType.BUNDLE_LEG.value
        and row.intent_role == IntentRole.CHILD.value
        and row.parent_intent_id is not None
    )
