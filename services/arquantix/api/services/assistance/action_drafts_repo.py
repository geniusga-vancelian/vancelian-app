"""Persistance audit des brouillons transactionnels CAL (``assistance_action_drafts``).

Phase 3 : validation stricte du payload métier avant écriture
(``action_draft_payload_schemas.validate_action_draft_business_payload``).

Phase 4 : machine d'état ``payload["_lifecycle"]`` + transitions auditées —
``action_lifecycle``.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.assistance.action_draft_contract import merge_business_payload_with_contract
from services.assistance.action_draft_payload_schemas import (
    InvalidActionDraftBusinessPayload,
    validate_action_draft_business_payload,
)
from services.assistance.action_lifecycle import (
    ActionDraftLifecycleState,
    apply_transition_to_sql_row,
    effective_lifecycle_state,
    get_lifecycle_block,
    is_action_draft_expired,
    LIFECYCLE_PAYLOAD_KEY,
    merge_lifecycle_block,
    persist_lifecycle_transition_audit_with_log,
    seed_initial_lifecycle,
    TriggerSource,
)
from services.assistance.action_registry import get_action_definition
from database import AssistanceActionDraft

logger = logging.getLogger(__name__)


def _active_macro_drafts(
    db: Session,
    *,
    conversation_id: UUID,
) -> list[AssistanceActionDraft]:
    return (
        db.query(AssistanceActionDraft)
        .filter(
            AssistanceActionDraft.conversation_id == conversation_id,
            AssistanceActionDraft.status == "draft",
        )
        .order_by(AssistanceActionDraft.created_at.asc())
        .all()
    )


def supersede_previous_drafts(
    db: Session,
    *,
    conversation_id: UUID,
    trigger_source: TriggerSource = "runtime_tool",
) -> int:
    """Remplace les brouillons actifs : ``superseded`` ou ``expired`` si TTL dépassé."""
    rows = _active_macro_drafts(db, conversation_id=conversation_id)
    n = 0
    for row in rows:
        pl = dict(row.payload if isinstance(row.payload, dict) else {})
        if is_action_draft_expired(payload=pl):
            evt = apply_transition_to_sql_row(
                row,
                to_lifecycle="expired",
                reason="ttl_expired",
                trigger="system",
            )
            persist_lifecycle_transition_audit_with_log(db, evt=evt)
            n += 1
            continue
        evt = apply_transition_to_sql_row(
            row,
            to_lifecycle="superseded",
            reason="superseded_by_new_action",
            trigger=trigger_source,
        )
        persist_lifecycle_transition_audit_with_log(db, evt=evt)
        n += 1
    if n:
        db.flush()
    return n


def cancel_active_action_drafts(
    db: Session,
    *,
    conversation_id: UUID,
    trigger_source: TriggerSource = "user",
) -> int:
    """Annule tous les macro-``draft`` actifs pour la conversation (ex. abandon QCM)."""
    rows = _active_macro_drafts(db, conversation_id=conversation_id)
    n = 0
    for row in rows:
        pl = dict(row.payload if isinstance(row.payload, dict) else {})
        if is_action_draft_expired(payload=pl):
            evt = apply_transition_to_sql_row(
                row,
                to_lifecycle="expired",
                reason="ttl_expired",
                trigger="system",
            )
        else:
            evt = apply_transition_to_sql_row(
                row,
                to_lifecycle="cancelled",
                reason="user_cancelled",
                trigger=trigger_source,
            )
        persist_lifecycle_transition_audit_with_log(db, evt=evt)
        n += 1
    if n:
        db.flush()
    return n


def create_action_draft(
    db: Session,
    *,
    conversation_id: UUID,
    client_id: UUID,
    action_type: str,
    payload: dict[str, Any],
) -> AssistanceActionDraft:
    """Insère un brouillon. Lève ``InvalidActionDraftBusinessPayload`` si invalide."""

    try:
        normalized = validate_action_draft_business_payload(action_type, dict(payload))
    except InvalidActionDraftBusinessPayload as exc:
        logger.warning(
            "action_draft.invalid_business_payload "
            "reason=invalid_action_draft_payload action_type=%s errors=%s",
            exc.action_type,
            exc.errors,
        )
        raise

    meta = get_action_definition(action_type)
    if not meta.allow_parallel_actions:
        supersede_previous_drafts(
            db, conversation_id=conversation_id, trigger_source="runtime_tool"
        )

    full_payload = merge_business_payload_with_contract(
        dict(normalized),
        action_type=action_type,
    )
    seed_initial_lifecycle(full_payload, action_type=action_type, trigger="runtime_tool")
    row = AssistanceActionDraft(
        conversation_id=conversation_id,
        client_id=client_id,
        action_type=action_type,
        status="draft",
        payload=dict(full_payload),
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


def mark_action_draft_confirmed_for_client(
    db: Session,
    *,
    conversation_id: UUID,
    client_id: UUID,
    draft_id: UUID,
) -> AssistanceActionDraft:
    """Passage backend vers ``confirmed`` (exécution d'ordre hors scope)."""
    row = (
        db.query(AssistanceActionDraft)
        .filter(
            AssistanceActionDraft.id == draft_id,
            AssistanceActionDraft.client_id == client_id,
            AssistanceActionDraft.conversation_id == conversation_id,
        )
        .first()
    )
    if row is None:
        raise ValueError("action_draft_introuvable")
    if row.status != "draft":
        raise ValueError("action_draft_non_active_pour_confirmation")
    pl = dict(row.payload if isinstance(row.payload, dict) else {})
    if is_action_draft_expired(payload=pl):
        raise ValueError("action_draft_expired_cannot_confirm")
    lc = effective_lifecycle_state(column_status=row.status, payload=pl)
    if lc == "confirmed":
        return row
    evt = apply_transition_to_sql_row(
        row,
        to_lifecycle="confirmed",
        reason="confirmed_by_user",
        trigger="user",
    )
    persist_lifecycle_transition_audit_with_log(db, evt=evt)
    db.flush()
    return row


def pending_action_memory_snapshot(
    db: Session,
    *,
    conversation_id: UUID,
) -> Optional[dict[str, Any]]:
    """Dernier brouillon actif pour la conversation (statut macro ``draft``)."""
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

    if is_action_draft_expired(payload=pl):
        evt = apply_transition_to_sql_row(
            row,
            to_lifecycle="expired",
            reason="ttl_expired",
            trigger="system",
        )
        persist_lifecycle_transition_audit_with_log(db, evt=evt)
        db.flush()
        return None

    af_raw = pl.get("amount_from")
    amount_from: Optional[float] = None
    if af_raw is not None:
        try:
            amount_from = float(af_raw)
        except (TypeError, ValueError):
            amount_from = None
    cfr = pl.get("currency_from")
    currency_from = (
        str(cfr).strip().upper()[:16]
        if isinstance(cfr, str) and str(cfr).strip()
        else None
    )
    cc = pl.get("cal_contract")
    cal_expires_at: Optional[str] = None
    if isinstance(cc, dict) and isinstance(cc.get("expires_at"), str):
        cal_expires_at = str(cc["expires_at"]).strip() or None
    lifecycle_state = effective_lifecycle_state(
        column_status=row.status,
        payload=pl,
    )

    snap: dict[str, Any] = {
        "action_draft_id": str(row.id),
        "action_type": row.action_type,
        "status": row.status,
        "lifecycle_state": lifecycle_state,
        "cal_expires_at": cal_expires_at,
        "target_kind": pl.get("target_kind"),
        "target_id": pl.get("target_id"),
        "stage": pl.get("stage"),
        "amount_from": amount_from,
        "currency_from": currency_from,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    return snap


def get_latest_active_draft_row(
    db: Session,
    *,
    conversation_id: UUID,
    action_type: Optional[str] = None,
) -> Optional[AssistanceActionDraft]:
    """Dernier brouillon macro-``draft`` (par ``created_at`` desc), optionnel filtré ``action_type``."""

    q = (
        db.query(AssistanceActionDraft)
        .filter(
            AssistanceActionDraft.conversation_id == conversation_id,
            AssistanceActionDraft.status == "draft",
        )
        .order_by(AssistanceActionDraft.created_at.desc())
    )
    if action_type:
        at = action_type.strip()
        if at:
            q = q.filter(AssistanceActionDraft.action_type == at)
    row = q.first()
    if row is None:
        return None
    pl = row.payload if isinstance(row.payload, dict) else {}
    if is_action_draft_expired(payload=pl):
        evt = apply_transition_to_sql_row(
            row,
            to_lifecycle="expired",
            reason="ttl_expired",
            trigger="system",
        )
        persist_lifecycle_transition_audit_with_log(db, evt=evt)
        db.flush()
        return None
    return row


def persist_action_draft_business_update(
    db: Session,
    *,
    row: AssistanceActionDraft,
    business_payload: dict[str, Any],
    lifecycle_to: Optional[ActionDraftLifecycleState] = None,
    lifecycle_reason: str = "business_payload_updated",
) -> AssistanceActionDraft:
    """Réécrit le payload métier + ``cal_contract`` en conservant ``_lifecycle``."""

    if row.status != "draft":
        raise ValueError("action_draft_non_active_pour_mise_a_jour")

    prev_lc = dict(get_lifecycle_block(row.payload))
    try:
        normalized = validate_action_draft_business_payload(
            row.action_type,
            dict(business_payload),
        )
    except InvalidActionDraftBusinessPayload as exc:
        logger.warning(
            "action_draft.update_invalid_business action_type=%s errors=%s",
            exc.action_type,
            exc.errors,
        )
        raise

    full = merge_business_payload_with_contract(
        dict(normalized),
        action_type=row.action_type,
    )
    if prev_lc:
        full[LIFECYCLE_PAYLOAD_KEY] = prev_lc
    if lifecycle_to is not None:
        merge_lifecycle_block(
            full,
            state=lifecycle_to,
            reason=lifecycle_reason,
            trigger="runtime_tool",
        )
    row.payload = dict(full)
    db.flush()
    logger.info(
        "action_draft.updated conv=%s draft_id=%s action_type=%s",
        row.conversation_id,
        row.id,
        row.action_type,
    )
    return row


__all__ = [
    "cancel_active_action_drafts",
    "create_action_draft",
    "get_latest_active_draft_row",
    "mark_action_draft_confirmed_for_client",
    "pending_action_memory_snapshot",
    "persist_action_draft_business_update",
    "supersede_previous_drafts",
]
