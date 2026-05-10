"""Timeline admin — observabilité runtime par tour utilisateur (debug console).

Construit une vue rejouable **sans nouveau stockage** : messages + lignes
``assistance_agent_decisions`` + projection du brouillon macro actif
(``AssistanceActionDraft``). Les ``FieldAttribution`` sont des inférences
documentées jusqu'à instrumentation explicite (Phase ultérieure).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import (
    AssistanceActionDraft,
    AssistanceAgentDecision,
    AssistanceMessage,
)

from services.assistance.agents.orchestration_context import (
    ROUTING_CONFIDENCE_CRYPTO_INTENT_DRAFT_MIN,
)

_DRAFT_PROJECTION_KEYS: tuple[str, ...] = (
    "action_type",
    "stage",
    "draft_origin",
    "target_kind",
    "target_id",
    "amount_from",
    "currency_from",
    "lifecycle_state",
    "slots_target_asset_raw",
    "slots_target_asset_resolved_id",
    "slots_source_account_raw",
    "slots_source_account_resolved_id",
    "slots_amount_value",
    "slots_amount_currency",
    "backend_validation_status",
    "confirmation_status",
)


def _iso(ts: Optional[dt.datetime]) -> Optional[str]:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc).isoformat()


def _safe_dict(d: Any) -> dict[str, Any]:
    return dict(d) if isinstance(d, dict) else {}


def _truncate(obj: Any, *, max_chars: int = 12000) -> Any:
    s = json.dumps(obj, default=str, ensure_ascii=False)
    if len(s) <= max_chars:
        return json.loads(s)
    return {"_truncated": True, "preview": s[:max_chars], "original_len": len(s)}


def _active_macro_draft_projection(db: Session, *, conversation_id: UUID) -> dict[str, Any]:
    row = (
        db.query(AssistanceActionDraft)
        .filter(
            AssistanceActionDraft.conversation_id == conversation_id,
            AssistanceActionDraft.status == "draft",
        )
        .order_by(AssistanceActionDraft.updated_at.desc())
        .first()
    )
    if row is None:
        return {}

    pl = row.payload if isinstance(row.payload, dict) else {}
    lc_block = pl.get("_lifecycle")
    lc_state = (
        lc_block.get("state")
        if isinstance(lc_block, dict)
        and isinstance(lc_block.get("state"), str)
        else None
    )

    proj: dict[str, Any] = {
        "draft_id": str(row.id),
        "action_type": row.action_type,
        "draft_status_macro": row.status,
    }
    for k in ("stage", "target_kind", "target_id", "amount_from", "currency_from"):
        if pl.get(k) is not None:
            proj[k] = pl[k]
    if row.action_type == "crypto_investment_intent" and pl.get("draft_origin"):
        proj["draft_origin"] = pl.get("draft_origin")
    if row.action_type == "crypto_investment_intent":
        slots = pl.get("slots") if isinstance(pl.get("slots"), dict) else {}
        sta = slots.get("target_asset") if isinstance(slots.get("target_asset"), dict) else {}
        ssa = slots.get("source_account") if isinstance(slots.get("source_account"), dict) else {}
        sam = slots.get("amount") if isinstance(slots.get("amount"), dict) else {}
        if sta.get("raw") is not None:
            proj["slots_target_asset_raw"] = sta.get("raw")
        if sta.get("resolved_id") is not None:
            proj["slots_target_asset_resolved_id"] = sta.get("resolved_id")
        if ssa.get("raw") is not None:
            proj["slots_source_account_raw"] = ssa.get("raw")
        if ssa.get("resolved_id") is not None:
            proj["slots_source_account_resolved_id"] = ssa.get("resolved_id")
        if sam.get("value") is not None:
            proj["slots_amount_value"] = sam.get("value")
        if sam.get("currency") is not None:
            proj["slots_amount_currency"] = sam.get("currency")
        bv = pl.get("backend_validation") if isinstance(pl.get("backend_validation"), dict) else {}
        if bv.get("status") is not None:
            proj["backend_validation_status"] = bv.get("status")
        cfir = pl.get("confirmation") if isinstance(pl.get("confirmation"), dict) else {}
        if cfir.get("status") is not None:
            proj["confirmation_status"] = cfir.get("status")
    if lc_state:
        proj["lifecycle_state"] = lc_state
    return proj


def _flatten_for_diff(proj: dict[str, Any]) -> dict[str, Any]:
    return {k: proj.get(k) for k in _DRAFT_PROJECTION_KEYS if k in proj}


def _diff_maps(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[dict[str, Any]]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    out: list[dict[str, Any]] = []
    for k in keys:
        b, a = before.get(k), after.get(k)
        if b != a:
            out.append({"field": k, "before": b, "after": a})
    return out


def _merge_sources_from_crypto_buy_trace(result_summary: Any) -> Optional[list[str]]:
    if not isinstance(result_summary, dict):
        return None
    # ``crypto_buy_start`` renvoie parfois ``merge_sources``
    ms = result_summary.get("merge_sources")
    return list(ms) if isinstance(ms, list) else None


def infer_slot_attributions_v0(
    *,
    user_plain: str,
    tool_traces: list[dict[str, Any]],
    draft_diff_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Heuristique v0 — remplacer par provenance stricte quand disponible."""

    ux = user_plain.strip().lower()
    slots: dict[str, dict[str, Any]] = {}

    # Montant depuis texte user
    if re.search(r"\d", ux) and re.search(
        r"(€|eur|euro|\beur\b|\$|usd|\d+\s*k\b)", ux, re.IGNORECASE
    ):
        amt_m = re.search(
            r"(\d+[.,]?\d*)\s*(€|eur|euros?|\bEUR\b|\$|usd)?",
            user_plain,
            re.IGNORECASE,
        )
        if amt_m:
            raw = amt_m.group(1).replace(",", ".")
            try:
                val = float(raw)
                slots["amount_from"] = {
                    "value": val,
                    "source": "user_explicit_in_text",
                    "confidence": 0.85,
                    "note": "regex_admin_infer_v0",
                }
            except ValueError:
                pass

    for d in draft_diff_entries:
        field = str(d.get("field") or "")
        if field != "amount_from" or "amount_from" in slots:
            continue
        before_n, after_n = d.get("before"), d.get("after")
        if before_n is None and after_n is not None:
            src = "unknown_injection"
            conf = 0.35
            for tr in tool_traces:
                if tr.get("tool_name") != "crypto_buy_start":
                    continue
                ms = _merge_sources_from_crypto_buy_trace(tr.get("result_summary"))
                if ms:
                    src = "merge_crypto_buy_intake"
                    conf = 0.55
                else:
                    src = "crypto_buy_start_tool_output"
                    conf = 0.5
                break
            slots["amount_from"] = {
                "value": after_n,
                "source": src,
                "confidence": conf,
                "note": "admin_infer_v0_no_single_writer",
            }

    return {"slots": slots, "_engine": "infer_slot_attributions_v0"}


def _serialize_decision_row(d: AssistanceAgentDecision) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "agent_id": d.agent_id,
        "iteration": int(d.iteration),
        "tool_name": d.tool_name,
        "autonomy_level": d.autonomy_level,
        "message_id": str(d.message_id) if d.message_id else None,
        "arguments": _truncate(_safe_dict(d.arguments_json)),
        "result_summary": _truncate(d.result_summary)
        if d.result_summary is not None
        else None,
        "error_code": d.error_code,
        "created_at": _iso(d.created_at),
        "duration_ms": d.duration_ms,
    }


def _router_runtime_panel(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_kind": args.get("decision_kind"),
        "routed_agent_id": args.get("agent_id"),
        "router_confidence": args.get("confidence"),
        "intent_classification": args.get("intent_classification"),
        "cognitive_state": args.get("cognitive_state"),
        "objective": args.get("objective"),
        "orchestration": args.get("orchestration"),
        "conversation_state": args.get("conversation_state"),
        "current_topic_block": (args.get("conversation_state") or {}).get("topic")
        if isinstance(args.get("conversation_state"), dict)
        else None,
        "pending_action_runtime": (args.get("conversation_state") or {}).get(
            "pending_action"
        )
        if isinstance(args.get("conversation_state"), dict)
        else None,
    }


def _crypto_investment_intent_p1_trace(
    *,
    cognitive_runtime_view: Optional[dict[str, Any]],
    interim_decisions: list[AssistanceAgentDecision],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if cognitive_runtime_view is None or not isinstance(cognitive_runtime_view, dict):
        return out
    orch = cognitive_runtime_view.get("orchestration")
    if not isinstance(orch, dict):
        return out
    if str(orch.get("transaction_kind") or "").strip().lower() != "crypto_investment_intent":
        return out
    rc = orch.get("routing_confidence")
    gate = False
    rc_f: Optional[float] = None
    if rc is not None:
        try:
            rc_f = float(rc)
            gate = rc_f < ROUTING_CONFIDENCE_CRYPTO_INTENT_DRAFT_MIN
        except (TypeError, ValueError):
            rc_f = None
            gate = False
    out["router"] = {
        "routing_confidence": rc_f if rc_f is not None else rc,
        "draft_floor": ROUTING_CONFIDENCE_CRYPTO_INTENT_DRAFT_MIN,
        "start_tool_gated_below_floor": gate,
    }
    last_resolve: Optional[dict[str, Any]] = None
    last_confirm: Optional[dict[str, Any]] = None
    for d in reversed(interim_decisions):
        if d.tool_name == "crypto_investment_intent_resolve" and last_resolve is None:
            rs = d.result_summary if isinstance(d.result_summary, dict) else None
            if isinstance(rs, dict):
                last_resolve = {
                    k: rs.get(k)
                    for k in (
                        "ok",
                        "clarification",
                        "clarification_reason",
                        "clarification_options_count",
                        "errors",
                    )
                    if k in rs
                }
        elif d.tool_name == "crypto_investment_intent_confirm" and last_confirm is None:
            rs = d.result_summary if isinstance(d.result_summary, dict) else None
            if isinstance(rs, dict):
                last_confirm = {
                    k: rs.get(k)
                    for k in ("ok", "confirmation_status", "lifecycle_terminal", "error")
                    if k in rs
                }
        if last_resolve is not None and last_confirm is not None:
            break
    if last_resolve is not None:
        out["last_resolve_snapshot"] = last_resolve
    if last_confirm is not None:
        out["last_confirm_snapshot"] = last_confirm
    return out


def build_runtime_debug_timeline(
    db: Session,
    *,
    conversation_id: UUID,
) -> dict[str, Any]:
    """Assemble la timeline « debug console » pour une conversation."""

    msgs = (
        db.query(AssistanceMessage)
        .filter(AssistanceMessage.conversation_id == conversation_id)
        .order_by(AssistanceMessage.turn_index.asc(), AssistanceMessage.created_at.asc())
        .all()
    )
    decisions = (
        db.query(AssistanceAgentDecision)
        .filter(AssistanceAgentDecision.conversation_id == conversation_id)
        .order_by(AssistanceAgentDecision.created_at.asc())
        .all()
    )

    router_by_user_msg = {
        r.message_id: r
        for r in decisions
        if r.tool_name == "router_classify" and r.message_id is not None
    }

    user_positions = [i for i, m in enumerate(msgs) if m.role == "user"]
    turns_out: list[dict[str, Any]] = []
    prev_draft_flat: dict[str, Any] = {}

    for u_pos, um_idx in enumerate(user_positions):
        um = msgs[um_idx]
        assistants: list[AssistanceMessage] = []
        for j in range(um_idx + 1, len(msgs)):
            if msgs[j].role == "user":
                break
            if msgs[j].role == "assistant":
                assistants.append(msgs[j])

        window_start = um.created_at
        next_user_ts: Optional[dt.datetime] = (
            msgs[user_positions[u_pos + 1]].created_at
            if u_pos + 1 < len(user_positions)
            else None
        )
        if assistants:
            window_end = max(a.created_at for a in assistants)
        elif next_user_ts is not None:
            window_end = next_user_ts
        else:
            window_end = dt.datetime.now(dt.timezone.utc)

        interim: list[AssistanceAgentDecision] = []
        for d in decisions:
            ts = d.created_at
            if ts is None or window_start is None:
                continue
            if ts < window_start or ts > window_end:
                continue
            if d.tool_name == "router_classify":
                continue
            interim.append(d)

        router_row = router_by_user_msg.get(um.id)
        rargs = _safe_dict(router_row.arguments_json) if router_row else {}

        tool_traces = [_serialize_decision_row(d) for d in interim]

        after_proj = _active_macro_draft_projection(db, conversation_id=conversation_id)
        after_flat = _flatten_for_diff(after_proj)
        draft_diff = _diff_maps(prev_draft_flat, after_flat)
        prev_draft_flat = dict(after_flat)

        runtime_trace_steps: list[str] = []
        if router_row:
            runtime_trace_steps.append(
                f"router → {rargs.get('agent_id') or '?'}"
                f" ({rargs.get('decision_kind') or '?'})"
            )
        for d in interim:
            if d.tool_name in (
                "conversation_resolution",
                "conversation_resolution_llm_invalid",
                "action_draft_lifecycle",
            ):
                runtime_trace_steps.append(
                    f"{d.tool_name} → {(_safe_dict(d.arguments_json).get('resolution_type') or _safe_dict(d.arguments_json).get('new_state') or _safe_dict(d.arguments_json).get('reason') or 'event')}"
                )
            elif d.tool_name not in ("router_classify",):
                runtime_trace_steps.append(f"tool → {d.tool_name}")

        attributions = infer_slot_attributions_v0(
            user_plain=um.content or "",
            tool_traces=tool_traces,
            draft_diff_entries=draft_diff,
        )

        cognitive_view = _router_runtime_panel(rargs) if router_row else None

        turns_out.append(
            {
                "turn_index": int(um.turn_index),
                "user_message_id": str(um.id),
                "user_content_preview": (um.content or "")[:2000],
                "window": {
                    "start": _iso(window_start),
                    "end": _iso(window_end),
                },
                "cognitive_runtime_view": cognitive_view,
                "crypto_investment_intent_trace": _crypto_investment_intent_p1_trace(
                    cognitive_runtime_view=cognitive_view,
                    interim_decisions=interim,
                ),
                "action_state": {
                    "projected_active_draft": after_proj,
                    "draft_field_diff_vs_previous_user_turn": draft_diff,
                },
                "runtime_decision_trace": runtime_trace_steps,
                "tool_traces": tool_traces,
                "assistant_message_ids": [str(a.id) for a in assistants],
                "slot_attribution_infer_v0": attributions,
            }
        )

    return {
        "conversation_id": str(conversation_id),
        "schema_version": "runtime_debug_timeline_v1",
        "turns": turns_out,
        "note": (
            "Les attributions `slot_attribution_infer_v0` sont heuristiques admin ; "
            "instrumenter merge_intake / LLM / draft pour une provenance stricte."
        ),
    }


__all__ = [
    "build_runtime_debug_timeline",
    "infer_slot_attributions_v0",
]
