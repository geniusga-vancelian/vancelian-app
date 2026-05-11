"""Court-circuits CAL achat crypto (agent ``action``).

1. Après tap « Confirmer » sur la QCM « lancer le trade ? » — injection
   synthétique ``crypto_buy_start`` → widget ``invest_confirmation``.

2. Follow-up montant seul — émet la QCM préalable (sans LLM) si le contexte
   assistant cadré un achat crypto.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared.classify_actor import ActorKind

if TYPE_CHECKING:
    from services.assistance.agents.base import AgentInput

from services.assistance.agents.tools.action import crypto_buy_start
from services.assistance.agents.tools.shared.deterministic_intake import (
    assistant_recent_frames_crypto_buy_intent,
    extract_intake_signals,
    infer_crypto_symbol_from_recent_turns,
    merge_crypto_buy_intake,
    resolve_intake_user_text,
)

logger = logging.getLogger(__name__)


def drain_embeds_for_dedup(
    ctx: ToolContext,
    *,
    embeds_collected: list[dict[str, Any]],
    embeds_seen_keys: set[tuple[str, str]],
) -> None:
    for emb in list(ctx.embeds_to_emit):
        if not isinstance(emb, dict):
            continue
        emb_type = str(emb.get("type") or "").strip()
        if not emb_type:
            continue
        emb_key_value = (
            str(emb.get("transaction_id") or "")
            or str(emb.get("slug") or "")
            or str(emb.get("id") or "")
            or str(emb.get("key") or "")
        )
        dedup_key = (emb_type, emb_key_value)
        if dedup_key in embeds_seen_keys:
            continue
        embeds_seen_keys.add(dedup_key)
        embeds_collected.append(emb)
    ctx.embeds_to_emit.clear()


def _snapshot_matches_intent_pending(
    pend: dict[str, Any],
    *,
    sym_u: str,
    amt: float,
    currency_from: Optional[str],
) -> bool:
    if str(pend.get("target_kind") or "").strip().lower() != "crypto_buy":
        return False
    if str(pend.get("target_id") or "").strip().upper() != str(sym_u).strip().upper():
        return False
    try:
        if abs(float(pend.get("amount_from")) - float(amt)) > 0.02:
            return False
    except (TypeError, ValueError):
        return False
    pc = pend.get("currency_from")
    pcy = (
        str(pc).strip().upper()
        if isinstance(pc, str) and str(pc).strip()
        else None
    )
    want = str(currency_from or "EUR").strip().upper()
    if pcy and pcy != want:
        return False
    return True


@dataclass(frozen=True)
class CryptoBuyCompactInjectPrepared:
    injection_messages: list[dict[str, Any]]
    tool_args: dict[str, Any]
    tool_result: dict[str, Any]


def try_prepare_crypto_buy_widget_after_launch_confirm(
    *,
    agent_input: "AgentInput",
    db: Session,
    user_id: int,
    actor_kind: ActorKind,
    conversation_id: str,
    correlation_id: str,
    audit_session_id: str,
    embeds_collected: list[dict[str, Any]],
    embeds_seen_keys: set[tuple[str, str]],
) -> Optional[CryptoBuyCompactInjectPrepared]:
    ms = getattr(agent_input, "memory_state", None) or {}
    if not isinstance(ms, dict):
        return None

    hint_raw = ms.get("user_choice_hint")
    hint_l = str(hint_raw).strip().lower() if isinstance(hint_raw, str) else ""
    if hint_l not in crypto_buy_start.CRYPTO_BUY_LAUNCH_CONFIRM_HINTS:
        return None

    pend_raw = ms.get("pending_action")
    pend = pend_raw if isinstance(pend_raw, dict) else {}
    if str(pend.get("stage") or "").strip().lower() != "awaiting_launch_confirm":
        return None

    rt = getattr(agent_input, "recent_turns", None)
    rt_list = list(rt) if isinstance(rt, list) else []
    intake = resolve_intake_user_text(
        user_message=getattr(agent_input, "user_message", None),
        memory_state=ms,
        recent_turns=rt_list or None,
    )

    merged = merge_crypto_buy_intake(
        tool_symbol=None,
        tool_amount_from=None,
        tool_currency_from=None,
        signals=extract_intake_signals("crypto_buy", intake),
        pending_action=pend,
        current_topic=ms["current_topic"]
        if isinstance(ms.get("current_topic"), dict)
        else None,
        recent_turns=rt_list,
    )

    sym_u = str(merged.get("symbol") or "").strip().upper()
    amt_raw = merged.get("amount_from")
    if not sym_u or amt_raw is None:
        return None
    try:
        amt_f = float(amt_raw)
    except (TypeError, ValueError):
        return None

    ccy = merged.get("currency_from")
    ccy_n = (
        str(ccy).strip().upper()[:16]
        if isinstance(ccy, str) and str(ccy).strip()
        else None
    )
    if ccy_n is None:
        ccy_n = "EUR"

    if not _snapshot_matches_intent_pending(
        pend, sym_u=sym_u, amt=amt_f, currency_from=ccy_n
    ):
        return None

    cog = ms.get("cognitive_state") if isinstance(ms.get("cognitive_state"), dict) else None
    obj = ms.get("objective") if isinstance(ms.get("objective"), dict) else None
    topic = ms.get("current_topic") if isinstance(ms.get("current_topic"), dict) else None

    ctx = ToolContext(
        db=db,
        client_id=str(ms["client_id"]) if ms.get("client_id") else None,
        person_id=str(ms["person_id"]) if ms.get("person_id") else None,
        user_id=user_id,
        actor_kind=actor_kind,
        agent_id="action",
        conversation_id=str(conversation_id),
        iteration=0,
        audit_session_id=audit_session_id,
        correlation_id=correlation_id,
        cognitive_state=cog,
        objective=obj,
        current_topic=topic,
        intake_user_text=intake or None,
        pending_action_snapshot=pend,
        recent_turns_snapshot=rt_list,
        user_choice_hint=hint_l,
    )

    tool_args = {"symbol": sym_u, "amount_from": amt_f, "currency_from": ccy_n}
    try:
        result = crypto_buy_start.execute(ctx, **tool_args)
    except Exception:
        logger.exception(
            "action_crypto_buy.widget_autorun.failed conv=%s", conversation_id
        )
        return None

    if (
        not isinstance(result, dict)
        or not result.get("ok")
        or result.get("mode") != "investment_confirmation_compact"
    ):
        return None

    drain_embeds_for_dedup(
        ctx, embeds_collected=embeds_collected, embeds_seen_keys=embeds_seen_keys
    )

    call_id = f"call_autowidget_{uuid4().hex[:24]}"
    return CryptoBuyCompactInjectPrepared(
        injection_messages=[
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": "crypto_buy_start",
                            "arguments": json.dumps(tool_args, default=str),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result, default=str),
            },
        ],
        tool_args=dict(tool_args),
        tool_result=result,
    )


def try_crypto_buy_early_launch_question_payload(
    *,
    agent_input: "AgentInput",
    db: Session,
    user_id: int,
    actor_kind: ActorKind,
    conversation_id: str,
    correlation_id: str,
    audit_session_id: str,
) -> Optional[dict[str, Any]]:
    ms = getattr(agent_input, "memory_state", None) or {}
    if not isinstance(ms, dict):
        return None

    pend_check = ms.get("pending_action")
    if isinstance(pend_check, dict):
        if (
            str(pend_check.get("action_type") or "").strip().lower()
            == "crypto_investment_intent"
        ):
            return None
        pst = str(pend_check.get("stage") or "").strip().lower()
        if pst in ("awaiting_launch_confirm", "confirmation"):
            return None

    rt = getattr(agent_input, "recent_turns", None)
    rt_list = list(rt) if isinstance(rt, list) else []

    intake = resolve_intake_user_text(
        user_message=getattr(agent_input, "user_message", None),
        memory_state=ms,
        recent_turns=rt_list or None,
    )
    sig = extract_intake_signals("crypto_buy", intake)
    sig_symbol = sig.get("symbol")
    sig_amount = sig.get("amount_from")

    merged = merge_crypto_buy_intake(
        tool_symbol=None,
        tool_amount_from=None,
        tool_currency_from=None,
        signals=sig,
        pending_action=ms["pending_action"]
        if isinstance(ms.get("pending_action"), dict)
        else None,
        current_topic=ms["current_topic"]
        if isinstance(ms.get("current_topic"), dict)
        else None,
        recent_turns=rt_list,
    )

    sym_u_m = merged.get("symbol")
    amt_m = merged.get("amount_from")
    if not sym_u_m or amt_m is None:
        return None

    # Même bulle complète : sym + montant (sinon ancien bug : tout refus si sym
    # dans le texte). Ou montant seul avec cadre « achater [actif] » en assistant.
    full_spec_in_turn = bool(sig_symbol) and sig_amount is not None
    framed_amount_followup = (
        sig_amount is not None
        and not sig_symbol
        and infer_crypto_symbol_from_recent_turns(rt_list) is not None
        and assistant_recent_frames_crypto_buy_intent(rt_list)
    )
    if not (full_spec_in_turn or framed_amount_followup):
        return None
    try:
        amt_f = float(amt_m)
    except (TypeError, ValueError):
        return None

    cog = ms.get("cognitive_state") if isinstance(ms.get("cognitive_state"), dict) else None
    obj = ms.get("objective") if isinstance(ms.get("objective"), dict) else None
    topic = ms.get("current_topic") if isinstance(ms.get("current_topic"), dict) else None

    pend_snap = ms["pending_action"] if isinstance(ms.get("pending_action"), dict) else None

    ctx = ToolContext(
        db=db,
        client_id=str(ms["client_id"]) if ms.get("client_id") else None,
        person_id=str(ms["person_id"]) if ms.get("person_id") else None,
        user_id=user_id,
        actor_kind=actor_kind,
        agent_id="action",
        conversation_id=str(conversation_id),
        iteration=0,
        audit_session_id=audit_session_id,
        correlation_id=correlation_id,
        cognitive_state=cog,
        objective=obj,
        current_topic=topic,
        intake_user_text=intake or None,
        pending_action_snapshot=pend_snap,
        recent_turns_snapshot=rt_list,
    )

    ccy_merge = merged.get("currency_from")
    cnorm = (
        str(ccy_merge).strip().upper()[:16]
        if isinstance(ccy_merge, str) and str(ccy_merge).strip()
        else None
    ) or "EUR"

    pl = crypto_buy_start.build_launch_trade_confirmation_interrupt_payload(
        ctx,
        sym_u=str(sym_u_m).strip().upper(),
        amt=amt_f,
        ccy_norm=cnorm,
        dest_human=crypto_buy_start.crypto_buy_destination_human(str(sym_u_m)),
    )

    if not pl:
        return None

    logger.info(
        "action_crypto_buy.early_launch_qcm conv=%s symbol=%s amount=%s",
        conversation_id,
        sym_u_m,
        amt_f,
    )

    return pl
