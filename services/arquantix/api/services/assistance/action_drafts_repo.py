"""Persistance audit des brouillons transactionnels CAL (``assistance_action_drafts``).

Phase 3 (step-up re-auth avant exécution) : reportée — aucune logique
métier d'ordre ici, uniquement trace + charge utile pour prompts / deep-links.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func as sql_func
from sqlalchemy.orm import Session

from database import AssistanceActionDraft

logger = logging.getLogger(__name__)


def supersede_previous_drafts(db: Session, *, conversation_id: UUID) -> int:
    """Marque les brouillons ``draft`` existants comme ``superseded``."""
    n = (
        db.query(AssistanceActionDraft)
        .filter(
            AssistanceActionDraft.conversation_id == conversation_id,
            AssistanceActionDraft.status == "draft",
        )
        .update(
            {"status": "superseded", "updated_at": sql_func.now()},
            synchronize_session=False,
        )
    )
    return int(n)


def create_action_draft(
    db: Session,
    *,
    conversation_id: UUID,
    client_id: UUID,
    action_type: str,
    payload: dict[str, Any],
) -> AssistanceActionDraft:
    supersede_previous_drafts(db, conversation_id=conversation_id)
    row = AssistanceActionDraft(
        conversation_id=conversation_id,
        client_id=client_id,
        action_type=action_type,
        status="draft",
        payload=dict(payload),
    )
    db.add(row)
    db.flush()
    logger.info(
        "action_draft.created conv=%s draft_id=%s action_type=%s",
        conversation_id,
        row.id,
        action_type,
    )
    return row


def pending_action_memory_snapshot(
    db: Session,
    *,
    conversation_id: UUID,
) -> Optional[dict[str, Any]]:
    """Dernier brouillon actif pour la conversation (statut ``draft``)."""
    row = (
        db.query(AssistanceActionDraft)
        .filter(
            AssistanceActionDraft.conversation_id == conversation_id,
            AssistanceActionDraft.status == "draft",
        )
        .order_by(AssistanceActionDraft.created_at.desc())
        .first()
    )
    if row is None:
        return None
    pl = row.payload if isinstance(row.payload, dict) else {}
    return {
        "action_draft_id": str(row.id),
        "action_type": row.action_type,
        "status": row.status,
        "target_kind": pl.get("target_kind"),
        "target_id": pl.get("target_id"),
        "stage": pl.get("stage"),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
