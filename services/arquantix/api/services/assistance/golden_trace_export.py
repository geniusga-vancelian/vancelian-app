"""Export « golden traces » JSONL pour replay et régressions (PR 4A).

Lit exclusivement les tables AssistanceMessage + AssistanceAgentDecision.
Read-only ; aucune config d’infra requise côté code (DATABASE_URL réutilisée).

Voir ``scripts/export_assistance_golden_traces.py``.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import AssistanceAgentDecision, AssistanceMessage

logger = logging.getLogger(__name__)

_SKIP_TOOLS_IN_TRACE = frozenset(
    {
        "router_classify",
    }
)


def _iso(dt_val: Optional[dt.datetime]) -> Optional[str]:
    if dt_val is None:
        return None
    if dt_val.tzinfo is None:
        dt_val = dt_val.replace(tzinfo=dt.timezone.utc)
    return dt_val.astimezone(dt.timezone.utc).isoformat()


def _finalize_message_type(ma: AssistanceMessage) -> str:
    mp = ma.message_payload or {}
    if not isinstance(mp, dict):
        mp = {}
    mt_raw = str(getattr(ma, "message_type", None) or "text").strip().lower()
    embeds = mp.get("embeds")
    has_embeds = isinstance(embeds, list) and len(embeds) > 0
    aq = mp.get("auto_qcm")

    if mt_raw == "choices":
        return "assistant_choices"
    has_auto = isinstance(aq, dict) and bool(aq.get("options"))
    if has_embeds and has_auto:
        return "assistant_text_with_embeds"  # metadata peut porter détail auto_qcm
    if has_auto:
        return "assistant_text_with_auto_qcm"
    if has_embeds:
        return "assistant_text_with_embeds"
    return "assistant_text"


def _embeds_payload(ma: AssistanceMessage) -> list[dict[str, Any]]:
    mp = ma.message_payload or {}
    if not isinstance(mp, dict):
        return []
    embeds = mp.get("embeds")
    return list(embeds) if isinstance(embeds, list) else []


def _serialize_turn_for_recent(m: AssistanceMessage) -> dict[str, Any]:
    mp_raw = getattr(m, "message_payload", None)
    mp: Optional[dict[str, Any]]
    if isinstance(mp_raw, dict):
        mp = mp_raw
    else:
        mp = None

    simplified: dict[str, Any] = {
        "turn_index": int(m.turn_index),
        "role": m.role,
        "content": m.content[:8000],  # limite fichier ; golden reste lisible
        "message_type": getattr(m, "message_type", None) or "text",
        "agent_used": getattr(m, "agent_used", None),
    }
    # Payload condensé (types d’embeds + flags)
    extras: dict[str, Any] = {}
    if mp:
        if isinstance(mp.get("embeds"), list):
            extras["embed_types"] = [
                str(e.get("type"))
                for e in mp["embeds"]
                if isinstance(e, dict) and e.get("type")
            ]
        if isinstance(mp.get("auto_qcm"), dict):
            extras["auto_qcm_prompt"] = (mp["auto_qcm"].get("prompt") or "")[:400]
            opts = mp["auto_qcm"].get("options")
            if isinstance(opts, list):
                extras["auto_qcm_option_count"] = len(opts)
    if extras:
        simplified["payload_hints"] = extras
    return simplified


def build_trace_for_user_turn(
    *,
    conversation_id: UUID,
    user_message: AssistanceMessage,
    assistants_for_turn: list[AssistanceMessage],
    router_decision_row: Optional[AssistanceAgentDecision],
    interim_decisions: list[AssistanceAgentDecision],
    recent_turn_messages: list[AssistanceMessage],
) -> dict[str, Any]:
    """Construit un dict ligne JSONL pour ``user_message`` (tour user)."""

    args = router_decision_row.arguments_json if router_decision_row else {}
    if not isinstance(args, dict):
        args = {}

    conv_state = args.get("conversation_state")
    if conv_state is not None and not isinstance(conv_state, dict):
        conv_state = {}

    router_decision_export: dict[str, Any] = {
        k: v
        for k, v in {
            "decision_kind": args.get("decision_kind"),
            "agent_id": args.get("agent_id"),
            "confidence": args.get("confidence"),
            "intent_classification": args.get("intent_classification"),
            "cognitive_state": args.get("cognitive_state"),
            "objective": args.get("objective"),
            "orchestration": args.get("orchestration"),
        }.items()
        if v is not None
    }
    if router_decision_row:
        router_decision_export["_persisted_router_row_id"] = str(router_decision_row.id)

    policy_gaps: list[dict[str, Any]] = []
    tools_called: list[str] = []
    for row in interim_decisions:
        if row.tool_name == "policy_data_need_reads":
            policy_gaps.append(
                {
                    "id": str(row.id),
                    "created_at": _iso(row.created_at),
                    "agent_id": row.agent_id,
                    "iteration": row.iteration,
                    "arguments": dict(row.arguments_json)
                    if isinstance(row.arguments_json, dict)
                    else {},
                    "result_summary": dict(row.result_summary)
                    if isinstance(row.result_summary, dict)
                    else row.result_summary,
                    "correlation_id": row.correlation_id,
                }
            )
        elif row.tool_name not in _SKIP_TOOLS_IN_TRACE:
            tools_called.append(row.tool_name)

    assistant_final = assistants_for_turn[-1] if assistants_for_turn else None
    embeds_final: list[dict[str, Any]] = []
    export_final_type = "assistant_unknown"
    agent_used_export: Optional[str] = None
    if assistant_final:
        embeds_final = _embeds_payload(assistant_final)
        export_final_type = _finalize_message_type(assistant_final)
        agent_used_export = getattr(assistant_final, "agent_used", None)

    trace = {
        "conversation_id": str(conversation_id),
        "turn_index": int(user_message.turn_index),
        "created_at": _iso(getattr(user_message, "created_at", None)),
        "user_message": user_message.content[:16000],
        "recent_turns": [_serialize_turn_for_recent(x) for x in recent_turn_messages],
        "conversation_state": dict(conv_state) if isinstance(conv_state, dict) else {},
        "router_decision": router_decision_export,
        "agent_used": agent_used_export,
        "tools_called": tools_called,
        "policy_gaps": policy_gaps,
        "final_message_type": export_final_type,
        "embeds": embeds_final,
        "metadata": {
            "schema_version": 1,
            "assistant_turn_indices": (
                [int(m.turn_index) for m in assistants_for_turn]
                if assistants_for_turn
                else []
            ),
            "assistant_ids": (
                [
                    str(i)
                    for i in (
                        getattr(m, "id", None) for m in assistants_for_turn
                    )
                    if i is not None
                ]
                if assistants_for_turn
                else []
            ),
        },
    }
    return trace


def export_conversation_turns_jsonl_strings(
    db: Session,
    *,
    conversation_id: UUID,
    recent_turn_cap: int = 24,
) -> list[str]:
    """Retourne des lignes JSON (sans trailing newline groupée)."""

    msgs = (
        db.query(AssistanceMessage)
        .filter(AssistanceMessage.conversation_id == conversation_id)
        .order_by(AssistanceMessage.turn_index.asc())
        .all()
    )
    router_rows_by_msg = {
        r.message_id: r
        for r in db.query(AssistanceAgentDecision)
        .filter(
            AssistanceAgentDecision.conversation_id == conversation_id,
            AssistanceAgentDecision.tool_name == "router_classify",
        )
        .all()
        if r.message_id is not None
    }
    decisions = (
        db.query(AssistanceAgentDecision)
        .filter(AssistanceAgentDecision.conversation_id == conversation_id)
        .order_by(AssistanceAgentDecision.created_at.asc())
        .all()
    )

    traces: list[str] = []
    user_ixs = [i for i, m in enumerate(msgs) if m.role == "user"]

    for u_pos, um_idx in enumerate(user_ixs):
        um = msgs[um_idx]

        assistants: list[AssistanceMessage] = []
        for j in range(um_idx + 1, len(msgs)):
            m = msgs[j]
            if m.role == "user":
                break
            if m.role == "assistant":
                assistants.append(m)

        router_row = router_rows_by_msg.get(um.id)

        window_start = um.created_at
        next_user_created: Optional[dt.datetime] = (
            msgs[user_ixs[u_pos + 1]].created_at
            if u_pos + 1 < len(user_ixs)
            else None
        )
        if assistants:
            window_end = max(a.created_at for a in assistants)
        elif next_user_created is not None:
            window_end = next_user_created
        else:
            window_end = dt.datetime.now(dt.timezone.utc)

        interim: list[AssistanceAgentDecision] = []
        for d in decisions:
            ts = d.created_at
            if ts < window_start or ts > window_end:
                continue
            if d.tool_name == "router_classify":
                continue
            interim.append(d)

        start_recent = max(0, um_idx - recent_turn_cap)
        recent_slice = msgs[start_recent : um_idx + 1]

        row_dict = build_trace_for_user_turn(
            conversation_id=conversation_id,
            user_message=um,
            assistants_for_turn=assistants,
            router_decision_row=router_row,
            interim_decisions=interim,
            recent_turn_messages=recent_slice,
        )
        traces.append(json.dumps(row_dict, ensure_ascii=False, default=str))
    return traces


def conversation_ids_between(
    db: Session,
    *,
    since: Optional[dt.datetime],
    until: Optional[dt.datetime],
    limit: int,
) -> list[UUID]:
    """IDs de conversations Assistance touchées pendant la fenêtre."""

    from database import AssistanceConversation

    q = db.query(AssistanceConversation.id)
    if since is not None:
        q = q.filter(AssistanceConversation.updated_at >= since)
    if until is not None:
        q = q.filter(AssistanceConversation.updated_at < until)
    q = q.order_by(AssistanceConversation.updated_at.desc()).limit(limit)
    return [r[0] for r in q.all()]


__all__ = [
    "export_conversation_turns_jsonl_strings",
    "build_trace_for_user_turn",
    "conversation_ids_between",
]
