"""État de conversation unifié (v1) — agrégation read-only de l’existant.

Ce module ne **décide** rien : il projette ``memory_state``, l’historique
récent, la charge utile du dernier tour bot, la décision router courante
et les snapshots cognitifs/objectif dans un contrat stable pour prompts,
audit et tests (cf. vision « conversation_state v1 »).

Réf. : discussion produit 2026 — unification sans big bang.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from services.assistance.agents.expected_answer_scope import (
    EXPECTED_ANSWER_SCOPE_KEY,
    PENDING_EXPECTATION_MEMORY_KEY,
)

# Clé ``memory_state`` / JSON (PR2) — snapshot agrégé pour prompt + futur audit.
CONVERSATION_STATE_MEMORY_KEY = "conversation_state"


class ConversationTopicState(BaseModel):
    """Sujet matérialisé (topic DB + dérivés lisibles)."""

    current_topic: Optional[str] = None
    active_product_id: Optional[str] = None
    active_instrument: Optional[str] = None
    active_issue: Optional[str] = None


class ConversationExpectationState(BaseModel):
    """Ce que le système attend comme prochaine entrée utilisateur."""

    expected_answer_type: Optional[str] = None
    expected_answer_scope: Optional[Dict[str, Any]] = None
    expected_answer_scope_id: Optional[str] = None
    last_bot_question: Optional[str] = None
    last_qcm_options: List[Dict[str, Any]] = Field(default_factory=list)
    pending_answer_expectation: bool = False


class ConversationCognitionState(BaseModel):
    """Snapshot cognitif (orthogonal au tag métier)."""

    stage: Optional[str] = None
    emotional_state: Optional[str] = None
    trust_level: Optional[str] = None
    engagement_level: Optional[str] = None


class ConversationOrchestrationState(BaseModel):
    """Dimensions orchestrateur (route_to / normalisation)."""

    last_agent: Optional[str] = None
    business_intent: Optional[str] = None
    transaction_kind: Optional[str] = None
    data_need: Optional[str] = None
    response_style: Optional[str] = None
    urgency: Optional[str] = None
    regulatory_risk: Optional[str] = None


class ConversationUxState(BaseModel):
    """Paramètres UX dérivés / objectif de tour."""

    stop_pushing: Optional[bool] = None
    widget_pressure: Optional[Literal["none", "low", "medium", "high"]] = None
    last_widgets_shown: List[str] = Field(default_factory=list)


class ConversationPendingActionState(BaseModel):
    """Brouillon transactionnel CAL actif (lisant ``memory_state.pending_action``)."""

    action_draft_id: Optional[str] = None
    action_type: Optional[str] = None
    status: Optional[str] = None
    target_kind: Optional[str] = None
    target_id: Optional[str] = None
    stage: Optional[str] = None
    # Champage JSON du brouillon (achat crypto, etc.) — exposé au prompt.
    amount_from: Optional[float] = None
    currency_from: Optional[str] = None


class ConversationState(BaseModel):
    """Contrat unique conversation_state v1."""

    topic: ConversationTopicState = Field(default_factory=ConversationTopicState)
    expectation: ConversationExpectationState = Field(
        default_factory=ConversationExpectationState
    )
    cognition: ConversationCognitionState = Field(
        default_factory=ConversationCognitionState
    )
    orchestration: ConversationOrchestrationState = Field(
        default_factory=ConversationOrchestrationState
    )
    ux: ConversationUxState = Field(default_factory=ConversationUxState)
    pending_action: ConversationPendingActionState = Field(
        default_factory=ConversationPendingActionState
    )


def render_conversation_state_for_prompt(state: ConversationState) -> str:
    """Sérialisation compacte pour injection future ``[CONVERSATION_STATE]``."""
    dumped = state.model_dump(mode="json", exclude_none=True)
    return json.dumps(dumped, ensure_ascii=False, separators=(",", ":"))


def _resolve_last_bot_turn(
    recent_turns: Optional[List[Any]],
    last_bot_turn: Any,
) -> Optional[Dict[str, Any]]:
    if isinstance(last_bot_turn, dict):
        return last_bot_turn
    rt = recent_turns or []
    if len(rt) >= 2:
        last = rt[-1]
        prev = rt[-2]
        if (
            isinstance(last, dict)
            and last.get("role") == "user"
            and isinstance(prev, dict)
            and prev.get("role") == "assistant"
        ):
            return prev
    for t in reversed(rt):
        if isinstance(t, dict) and t.get("role") == "assistant":
            return t
    return None


def _summarize_current_topic(raw: Any) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Dérive (résumé topic, product_code, instrument, issue/wiki) depuis JSONB."""
    if raw is None:
        return None, None, None, None
    if isinstance(raw, str) and raw.strip():
        return raw.strip(), None, None, None
    if not isinstance(raw, dict):
        return None, None, None, None

    kind = str(raw.get("kind") or "").strip().lower() or None
    summary = kind
    product = None
    instrument = None
    issue = None

    if kind == "vancelian_product":
        pc = raw.get("product_code")
        if isinstance(pc, str) and pc.strip():
            product = pc.strip().upper()
            summary = f"vancelian_product:{product}"
    elif kind == "instrument":
        sym = raw.get("instrument_symbol")
        if isinstance(sym, str) and sym.strip():
            instrument = sym.strip().upper()
            summary = f"instrument:{instrument}"
    elif kind == "topic_other":
        for key in ("knowledge_slug", "wiki_slug", "label"):
            v = raw.get(key)
            if isinstance(v, str) and v.strip():
                issue = v.strip()
                summary = f"topic_other:{issue}"
                break
        if summary == kind and issue is None:
            summary = kind

    return summary, product, instrument, issue


def _intent_to_emotional_state(raw: Any) -> Optional[str]:
    s = str(raw or "").strip().lower()
    if s in ("anger", "angry"):
        return "angry"
    if s in ("fear", "fearful", "anxious"):
        return "anxious"
    mapping = {
        "curiosity": "neutral",
        "compliance": "neutral",
        "transaction": "neutral",
        "opportunity": "neutral",
        "neutral": "neutral",
        "frustrated": "frustrated",
        "confused": "confused",
    }
    return mapping.get(s, s or None)


def _trust_display(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    try:
        f = float(raw)
    except (TypeError, ValueError):
        return str(raw).strip() or None
    if f >= 0.66:
        return "high"
    if f >= 0.33:
        return "medium"
    return "low"


def _expected_answer_type_from_scope(scope: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(scope, dict):
        return None
    kind = str(scope.get("kind") or "").strip().lower()
    if kind == "multiple_choice":
        return "qcm_choice"
    if kind == "listing_choice":
        return "listing_choice"
    return kind or None


def _expected_answer_type_from_turn(turn: Dict[str, Any]) -> Optional[str]:
    mt = str(turn.get("message_type") or "text").strip().lower()
    if mt == "choices":
        return "qcm_choice"
    mp = turn.get("message_payload")
    if isinstance(mp, dict) and isinstance(mp.get("auto_qcm"), dict):
        return "listing_choice"
    return None


def _scope_options_for_list(scope: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(scope, dict):
        return []
    ch = scope.get("choices")
    if not isinstance(ch, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in ch:
        if isinstance(item, dict):
            out.append(dict(item))
    return out


def _widgets_from_turn(turn: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(turn, dict):
        return []
    mp = turn.get("message_payload")
    if not isinstance(mp, dict):
        return []
    embeds = mp.get("embeds")
    if not isinstance(embeds, list):
        return []
    names: List[str] = []
    for e in embeds:
        if isinstance(e, dict):
            t = str(e.get("type") or "").strip()
            if t:
                names.append(t)
    return names


def _widget_pressure(
    widgets: List[str],
    *,
    emotional_state: Optional[str],
    stop_pushing: Optional[bool],
) -> Optional[Literal["none", "low", "medium", "high"]]:
    if emotional_state in ("angry", "frustrated", "anxious"):
        return "low"
    if stop_pushing is True:
        return "low"
    n = len(widgets)
    if n == 0:
        return "none"
    if n <= 2:
        return "low"
    if n <= 4:
        return "medium"
    return "high"


def build_conversation_state(
    *,
    memory_state: Optional[Dict[str, Any]],
    recent_turns: List[Any],
    last_bot_turn: Any = None,
    router_decision: Any = None,
    cognitive_state: Optional[Dict[str, Any]] = None,
    objective: Optional[Dict[str, Any]] = None,
) -> ConversationState:
    """Agrège l’état dispersé sans appliquer de logique métier nouvelle."""

    ms = dict(memory_state) if isinstance(memory_state, dict) else {}
    lb = _resolve_last_bot_turn(recent_turns, last_bot_turn)
    pa_raw = ms.get("pending_action")

    summary, prod, instr, issue = _summarize_current_topic(ms.get("current_topic"))

    topic = ConversationTopicState(
        current_topic=summary,
        active_product_id=prod,
        active_instrument=instr,
        active_issue=issue,
    )

    pend_raw = ms.get(PENDING_EXPECTATION_MEMORY_KEY)
    pending_mem = pend_raw if isinstance(pend_raw, dict) else None

    mp_lb: Optional[Dict[str, Any]] = None
    if isinstance(lb, dict):
        raw_mp = lb.get("message_payload")
        mp_lb = raw_mp if isinstance(raw_mp, dict) else None

    scope_obj: Optional[Dict[str, Any]] = None
    if isinstance(mp_lb, dict):
        sco = mp_lb.get(EXPECTED_ANSWER_SCOPE_KEY)
        scope_obj = dict(sco) if isinstance(sco, dict) else None

    if scope_obj is None and isinstance(pending_mem, dict) and pending_mem.get("choices"):
        scope_obj = dict(pending_mem)

    expected_type = _expected_answer_type_from_scope(scope_obj) or (
        _expected_answer_type_from_turn(lb) if isinstance(lb, dict) else None
    )

    pending_flag = isinstance(scope_obj, dict) and bool(scope_obj.get("choices"))

    scope_id_val: Optional[str] = None
    if isinstance(scope_obj, dict):
        sid = scope_obj.get("semantic_id") or scope_obj.get("scope_id")
        scope_id_val = str(sid).strip()[:160] if isinstance(sid, str) and sid.strip() else None

    last_question: Optional[str] = None
    if isinstance(lb, dict):
        last_question = str(lb.get("content") or "").strip() or None
        if (
            isinstance(mp_lb, dict)
            and isinstance(mp_lb.get("auto_qcm"), dict)
            and str(mp_lb["auto_qcm"].get("prompt") or "").strip()
        ):
            last_question = str(mp_lb["auto_qcm"]["prompt"]).strip()

    options_list = _scope_options_for_list(scope_obj)

    expectation = ConversationExpectationState(
        expected_answer_type=expected_type,
        expected_answer_scope=scope_obj if scope_obj else None,
        expected_answer_scope_id=scope_id_val,
        last_bot_question=last_question,
        last_qcm_options=options_list,
        pending_answer_expectation=pending_flag,
    )

    cog_raw = cognitive_state if isinstance(cognitive_state, dict) else {}
    cognition = ConversationCognitionState(
        stage=(
            str(cog_raw["conversation_stage"]).strip().lower()
            if cog_raw.get("conversation_stage") is not None
            else None
        ),
        emotional_state=_intent_to_emotional_state(cog_raw.get("emotional_intent")),
        trust_level=_trust_display(cog_raw.get("trust_level")),
        engagement_level=(
            str(cog_raw["knowledge_level"]).strip().lower()
            if cog_raw.get("knowledge_level") is not None
            else None
        ),
    )

    orch: Dict[str, Any] = {}
    if router_decision is not None:
        raw_orch = getattr(router_decision, "orchestration", None)
        if isinstance(raw_orch, dict):
            orch = raw_orch

    last_ag: Optional[str] = None
    if isinstance(lb, dict):
        au = lb.get("agent_used")
        if isinstance(au, str) and au.strip():
            last_ag = au.strip()
    if last_ag is None and router_decision is not None:
        rid = getattr(router_decision, "agent_id", None)
        if isinstance(rid, str) and rid.strip():
            last_ag = rid.strip()

    orchestration = ConversationOrchestrationState(
        last_agent=last_ag,
        business_intent=str(orch["business_intent"]).strip().lower()
        if orch.get("business_intent")
        else None,
        transaction_kind=str(orch["transaction_kind"]).strip().lower()
        if orch.get("transaction_kind")
        else None,
        data_need=str(orch["data_need"]).strip().lower()
        if orch.get("data_need")
        else None,
        response_style=str(orch["response_style"]).strip().lower()
        if orch.get("response_style")
        else None,
        urgency=str(orch["urgency"]).strip().lower() if orch.get("urgency") else None,
        regulatory_risk=str(orch["regulatory_risk"]).strip().lower()
        if orch.get("regulatory_risk")
        else None,
    )

    obj = objective if isinstance(objective, dict) else {}
    stop_push = obj.get("stop_pushing")
    stop_bool: Optional[bool]
    if isinstance(stop_push, bool):
        stop_bool = stop_push
    else:
        stop_bool = None

    widgets = _widgets_from_turn(lb)
    ux = ConversationUxState(
        stop_pushing=stop_bool,
        widget_pressure=_widget_pressure(
            widgets,
            emotional_state=cognition.emotional_state,
            stop_pushing=stop_bool,
        ),
        last_widgets_shown=widgets,
    )

    pending_action = ConversationPendingActionState()
    if isinstance(pa_raw, dict):
        raw_af = pa_raw.get("amount_from")
        parsed_amt: Optional[float] = None
        if isinstance(raw_af, (int, float)):
            parsed_amt = float(raw_af)
        elif isinstance(raw_af, str) and raw_af.strip():
            try:
                parsed_amt = float(raw_af.replace(",", ".").replace(" ", ""))
            except ValueError:
                parsed_amt = None

        pending_action = ConversationPendingActionState(
            action_draft_id=(
                str(pa_raw["action_draft_id"]).strip()
                if pa_raw.get("action_draft_id") is not None
                else None
            ),
            action_type=(
                str(pa_raw["action_type"]).strip().lower()
                if pa_raw.get("action_type")
                else None
            ),
            status=(
                str(pa_raw["status"]).strip().lower()
                if pa_raw.get("status")
                else None
            ),
            target_kind=(
                str(pa_raw["target_kind"]).strip().lower()
                if pa_raw.get("target_kind")
                else None
            ),
            target_id=(
                str(pa_raw["target_id"]).strip()
                if pa_raw.get("target_id")
                else None
            ),
            stage=(
                str(pa_raw["stage"]).strip().lower()
                if pa_raw.get("stage")
                else None
            ),
            amount_from=parsed_amt,
            currency_from=(
                str(pa_raw["currency_from"]).strip().upper()[:16]
                if isinstance(pa_raw.get("currency_from"), str)
                and pa_raw["currency_from"].strip()
                else None
            ),
        )

    return ConversationState(
        topic=topic,
        expectation=expectation,
        cognition=cognition,
        orchestration=orchestration,
        ux=ux,
        pending_action=pending_action,
    )


__all__ = [
    "CONVERSATION_STATE_MEMORY_KEY",
    "ConversationState",
    "ConversationTopicState",
    "ConversationExpectationState",
    "ConversationCognitionState",
    "ConversationOrchestrationState",
    "ConversationUxState",
    "ConversationPendingActionState",
    "build_conversation_state",
    "render_conversation_state_for_prompt",
]
