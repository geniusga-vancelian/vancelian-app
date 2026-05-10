"""Tool ``crypto_investment_intent_confirm`` — mise à jour ``confirmation.status`` hors LLM."""

from __future__ import annotations

import logging
from typing import Any, Optional

from uuid import UUID

from services.assistance.action_draft_contract import merge_business_payload_with_contract
from services.assistance.action_draft_payload_schemas import (
    InvalidActionDraftBusinessPayload,
    validate_action_draft_business_payload,
)
from services.assistance.action_drafts_repo import get_latest_active_draft_row
from services.assistance.action_lifecycle import (
    apply_transition_to_sql_row,
    effective_lifecycle_state,
    get_lifecycle_block,
    persist_lifecycle_transition_audit_with_log,
)
from services.assistance.agents.tools.action.crypto_investment_intent_logic import (
    infer_crypto_intent_confirmation_from_text,
)
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)

SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "crypto_investment_intent_confirm",
        "description": (
            "Enregistre la réponse utilisateur sur le récap **crypto_investment_intent** "
            "lorsque le brouillon est en attente de confirmation : parse **déterministe** "
            "du texte du tour (ou ``user_choice`` explicite) puis met à jour "
            "``confirmation.status`` et le cycle de vie (``confirmed`` / ``cancelled``). "
            "**Aucune** exécution d’ordre."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_choice": {
                    "type": "string",
                    "enum": ["confirmed", "declined"],
                    "description": (
                        "Choix explicite si le modèle l’identifie sans ambiguïté ; "
                        "sinon omettre pour utiliser le parse serveur sur le message utilisateur."
                    ),
                },
            },
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "action",
}


def _strip_business_root(row_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in row_payload.items()
        if k not in {"cal_contract", "_lifecycle"}
    }


def execute(
    ctx: ToolContext,
    *,
    user_choice: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    if not ctx.client_id:
        return {"ok": False, "error": "client_required", "flow": "crypto_investment_intent"}

    try:
        conv_uid = UUID(str(ctx.conversation_id))
    except (ValueError, AttributeError):
        return {"ok": False, "error": "bad_uuid", "flow": "crypto_investment_intent"}

    row = get_latest_active_draft_row(
        ctx.db,
        conversation_id=conv_uid,
        action_type="crypto_investment_intent",
    )
    if row is None:
        return {"ok": False, "error": "no_active_intent_draft", "flow": "crypto_investment_intent"}

    pl = dict(row.payload if isinstance(row.payload, dict) else {})
    lc = effective_lifecycle_state(column_status=row.status, payload=pl)
    if lc != "awaiting_confirmation":
        return {
            "ok": False,
            "error": "intent_not_awaiting_confirmation",
            "flow": "crypto_investment_intent",
            "lifecycle_state": lc,
        }

    conf = pl.get("confirmation") if isinstance(pl.get("confirmation"), dict) else {}
    if str(conf.get("status") or "") != "pending":
        return {
            "ok": False,
            "error": "confirmation_not_pending",
            "flow": "crypto_investment_intent",
            "confirmation_status": conf.get("status"),
        }

    summary = conf.get("summary")
    summary_s = str(summary).strip() if summary is not None else ""

    decision: Optional[str] = None
    if user_choice == "confirmed":
        decision = "confirm"
    elif user_choice == "declined":
        decision = "decline"
    else:
        inh = infer_crypto_intent_confirmation_from_text(ctx.intake_user_text)

        decision = inh if inh != "unknown" else None

    if decision is None:
        return {
            "ok": False,
            "error": "confirmation_parse_unknown",
            "flow": "crypto_investment_intent",
            "hint": (
                "Demandez une réponse explicite du type oui/non "
                "(ou repassez user_choice)."
            ),
        }

    business = _strip_business_root(pl)

    terminal_reason: str
    confirmation_status: str
    if decision == "confirm":
        confirmation_status = "confirmed"
        terminal_reason = "confirmed_by_user"
    else:
        confirmation_status = "declined"
        terminal_reason = "user_cancelled"

    business["confirmation"] = {
        "status": confirmation_status,
        "summary": summary_s or None,
    }

    prev_lc_block = dict(get_lifecycle_block(pl))
    try:
        normalized = validate_action_draft_business_payload(
            str(row.action_type), business
        )
    except InvalidActionDraftBusinessPayload as exc:
        logger.warning(
            "crypto_investment_intent_confirm.validate_failed conv=%s err=%s",
            ctx.conversation_id,
            exc.errors,
        )
        return {
            "ok": False,
            "error": "invalid_business_payload_after_confirmation",
            "flow": "crypto_investment_intent",
        }

    merged = merge_business_payload_with_contract(
        dict(normalized),
        action_type=str(row.action_type),
    )
    merged["_lifecycle"] = prev_lc_block
    row.payload = merged

    to_lifecycle = "confirmed" if decision == "confirm" else "cancelled"
    evt = apply_transition_to_sql_row(
        row,
        to_lifecycle=to_lifecycle,
        reason=terminal_reason,
        trigger="user",
    )
    persist_lifecycle_transition_audit_with_log(ctx.db, evt=evt)
    ctx.db.flush()

    logger.info(
        "crypto_investment_intent_confirm conv=%s draft=%s to=%s",
        ctx.conversation_id,
        row.id,
        to_lifecycle,
    )

    return {
        "ok": True,
        "flow": "crypto_investment_intent",
        "action_draft_id": str(row.id),
        "confirmation_status": confirmation_status,
        "lifecycle_terminal": to_lifecycle,
        "confirmation_summary": summary_s or None,
    }


__all__ = ["SPEC", "execute"]
