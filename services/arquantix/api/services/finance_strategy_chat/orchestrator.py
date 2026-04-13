"""Compliance Orchestrator for finance_strategy_chat V1."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .schemas import (
    StartRequest,
    StepRequest,
    StartResponse,
    StepResponse,
    StateResponse,
    Message,
    UIState,
    ClientProfile,
    NextQuestion,
    LastQuestion,
)
from .store import STORE
from .extraction import extract_patch
from .rules import evaluate
from .next_question import choose_next_question, load_default_registry
from .portfolio_engine import build_portfolio

DEFAULT_TTL_SECONDS = 60 * 60
QUESTIONS_REGISTRY = load_default_registry()


def _format_amount(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    try:
        val = float(value)
    except (ValueError, TypeError):
        return None
    return f"{int(val):,}".replace(",", " ")


def _assistant_ack_for_patch(patch: Dict[str, Any]) -> Optional[str]:
    updates = patch.get("updates", []) or []
    update_map = {u.get("path"): u.get("value") for u in updates if isinstance(u, dict)}
    if "goal.target_amount" in update_map:
        formatted = _format_amount(update_map.get("goal.target_amount"))
        if formatted:
            return f"OK, je note un objectif de {formatted}€ 👍"
    if "goal.initial_contribution_amount" in update_map:
        formatted = _format_amount(update_map.get("goal.initial_contribution_amount"))
        if formatted:
            return f"OK, je note {formatted}€ au départ 👍"
    if "goal.monthly_contribution_amount" in update_map:
        formatted = _format_amount(update_map.get("goal.monthly_contribution_amount"))
        if formatted:
            return f"OK, je note {formatted}€ par mois 👍"
    return None


def _normalize_project_type(profile: ClientProfile) -> None:
    raw = profile.goal.get("type")
    if not raw:
        return
    lower = str(raw).strip().lower()
    allowed = {"travel", "purchase", "real_estate", "retirement", "safety", "unknown"}
    if lower in allowed:
        profile.goal["type"] = lower
        return
    keywords = [
        ("travel", ["voyage", "vacances", "nyc", "maldives", "japon", "trip"]),
        ("purchase", ["achat", "voiture", "sac", "objet", "plaisir", "bien matériel", "cadeau"]),
        ("real_estate", ["immobilier", "apport", "maison", "appart", "logement", "locatif", "investissement"]),
        ("retirement", ["retraite", "long terme", "avenir", "liberté", "patrimoine"]),
        ("safety", ["sécurité", "filet", "matelas", "urgence", "serein", "serenit"]),
    ]
    for label, tokens in keywords:
        if any(token in lower for token in tokens):
            profile.goal["type"] = label
            profile.confidence["goal.type"] = max(profile.confidence.get("goal.type", 0.0), 0.85)
            return


def _apply_patch(profile: ClientProfile, patch: Dict[str, Any]) -> ClientProfile:
    updates = patch.get("updates", []) or []
    for upd in updates:
        path = upd.get("path")
        value = upd.get("value")
        confidence = float(upd.get("confidence", 0.9))
        if not path:
            continue
        if path.startswith("goal."):
            key = path.split("goal.", 1)[1]
            profile.goal[key] = value
            profile.confidence[path] = confidence
            continue
        if path.startswith("timeline."):
            key = path.split("timeline.", 1)[1]
            profile.timeline[key] = value
            profile.confidence[path] = confidence
            continue
        if path.startswith("capacity."):
            key = path.split("capacity.", 1)[1]
            profile.capacity[key] = value
            profile.confidence[path] = confidence
            continue
        if path.startswith("risk."):
            key = path.split("risk.", 1)[1]
            profile.risk[key] = value
            profile.confidence[path] = confidence
            continue
        if path.startswith("profile."):
            key = path.split("profile.", 1)[1]
        else:
            key = path
        if hasattr(profile, key):
            setattr(profile, key, value)
            profile.confidence[key] = confidence
    return profile


def _set_answer(answers: Dict[str, Any], key: str, value: Any, confidence: float) -> None:
    if value is None or value == "":
        return
    answers[key] = {"value": value, "confidence": confidence}


def _answers_from_profile(profile: ClientProfile, previous: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    answers = dict(previous or {})
    conf = profile.confidence

    _set_answer(answers, "goal.type", profile.goal.get("type"), float(conf.get("goal.type", 0.0)))
    _set_answer(answers, "goal.target_amount", profile.goal.get("target_amount"), float(conf.get("goal.target_amount", 0.0)))
    _set_answer(
        answers,
        "goal.initial_contribution_amount",
        profile.goal.get("initial_contribution_amount"),
        float(conf.get("goal.initial_contribution_amount", 0.0)),
    )
    description = profile.goal.get("description") or profile.project_summary
    desc_conf = conf.get("goal.description", conf.get("project_summary", 0.0))
    _set_answer(answers, "goal.description", description, float(desc_conf or 0.0))

    _set_answer(answers, "timeline.horizon_months", profile.timeline.get("horizon_months"), float(conf.get("timeline.horizon_months", 0.0)))
    _set_answer(answers, "timeline.horizon_years", profile.timeline.get("horizon_years"), float(conf.get("timeline.horizon_years", 0.0)))
    _set_answer(answers, "timeline.target_date", profile.timeline.get("target_date"), float(conf.get("timeline.target_date", 0.0)))

    _set_answer(answers, "capacity.monthly_contribution", profile.capacity.get("monthly_contribution"), float(conf.get("capacity.monthly_contribution", 0.0)))
    _set_answer(answers, "capacity.liquidity_need", profile.capacity.get("liquidity_need"), float(conf.get("capacity.liquidity_need", 0.0)))

    _set_answer(answers, "intent", profile.intent, float(conf.get("intent", 0.0)))
    _set_answer(answers, "project_summary", profile.project_summary, float(conf.get("project_summary", 0.0)))
    _set_answer(answers, "knowledge_level", profile.knowledge_level, float(conf.get("knowledge_level", 0.0)))

    return answers


def _progress(evaluation: Dict[str, Any]) -> Dict[str, int]:
    compliance = evaluation.get("compliance", {})
    required = compliance.get("required_fields", [])
    missing = compliance.get("missing_fields", [])
    total = max(len(required), 1)
    done = total - len(missing)
    phase = int((done / total) * 7)
    if phase < 0:
        phase = 0
    if phase > 7:
        phase = 7
    return {"phase": phase, "total_phases": 7}


def _state_payload(
    profile: ClientProfile,
    evaluation: Dict[str, Any],
    debug: Dict[str, Any],
    last_question: Optional[Dict[str, Any]] = None,
    answers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "profile": profile.model_dump(),
        "compliance": evaluation.get("compliance", {}),
        "debug": debug,
        "last_question": last_question,
        "answers": answers or {},
    }
    return payload


def start_session(request: StartRequest) -> StartResponse:
    session_id = str(uuid.uuid4())
    profile = ClientProfile()
    evaluation = evaluate(profile)
    answers = _answers_from_profile(profile)
    state = {"answers": answers}
    next_q = choose_next_question(state, QUESTIONS_REGISTRY)

    messages = [Message(role="assistant", content=next_q["question_text"])]
    ui = UIState(
        type=next_q["ui"]["type"],
        quick_replies=next_q["ui"].get("quick_replies"),
        allow_free_text=next_q["ui"].get("allow_free_text", True),
    )

    session = {
        "profile": profile.model_dump(),
        "last_question": LastQuestion(
            id=next_q["step_id"],
            text=next_q["question_text"],
            expected_fields=next_q.get("targets", []),
        ).model_dump(),
        "asked_questions": [next_q["step_id"]],
        "answers": answers,
        "debug": {},
    }
    STORE.set(session_id, session, DEFAULT_TTL_SECONDS)

    return StartResponse(
        session_id=session_id,
        messages=messages,
        ui=ui,
        progress=_progress(evaluation),
        state=_state_payload(profile, evaluation, session["debug"], session.get("last_question"), answers),
    )


def step_session(request: StepRequest) -> StepResponse:
    session = STORE.get(request.session_id)
    if not session:
        raise ValueError("Session not found")

    profile = ClientProfile(**(session.get("profile") or {}))
    last_question_data = session.get("last_question")
    last_question = LastQuestion(**last_question_data) if last_question_data else None
    asked = session.get("asked_questions") or []
    previous_answers = session.get("answers") or {}

    patch = extract_patch(profile, last_question, str(request.user_input.value))
    profile = _apply_patch(profile, patch.model_dump())
    _normalize_project_type(profile)
    answers = _answers_from_profile(profile, previous_answers)
    state = {"answers": answers}
    profile = _apply_patch(profile, patch.model_dump())
    _normalize_project_type(profile)

    evaluation = evaluate(profile)
    next_q = choose_next_question(state, QUESTIONS_REGISTRY)

    debug = session.get("debug", {})
    if patch.normalized and patch.normalized.money:
        debug["normalized_money"] = patch.normalized.money

    messages = []
    ack = _assistant_ack_for_patch(patch.model_dump())
    if ack:
        messages.append(Message(role="assistant", content=ack))
    messages.append(Message(role="assistant", content=next_q["question_text"]))

    if evaluation.get("ready"):
        session["portfolio"] = build_portfolio(profile)

    session.update(
        {
            "profile": profile.model_dump(),
            "last_question": LastQuestion(
                id=next_q["step_id"],
                text=next_q["question_text"],
                expected_fields=next_q.get("targets", []),
            ).model_dump(),
            "asked_questions": list({*asked, next_q["step_id"]}),
            "answers": answers,
            "debug": debug,
            "updated_at": datetime.utcnow().isoformat(),
        }
    )
    STORE.set(request.session_id, session, DEFAULT_TTL_SECONDS)

    return StepResponse(
        session_id=request.session_id,
        messages=messages,
        ui=UIState(
            type=next_q["ui"]["type"],
            quick_replies=next_q["ui"].get("quick_replies"),
            allow_free_text=next_q["ui"].get("allow_free_text", True),
        ),
        progress=_progress(evaluation),
        state=_state_payload(profile, evaluation, debug, session.get("last_question"), answers),
    )


def get_state(session_id: str) -> StateResponse:
    session = STORE.get(session_id)
    if not session:
        raise ValueError("Session not found")
    profile = ClientProfile(**(session.get("profile") or {}))
    evaluation = evaluate(profile)
    debug = session.get("debug", {})
    return StateResponse(
        session_id=session_id,
        state=_state_payload(profile, evaluation, debug, session.get("last_question"), session.get("answers")),
    )
