"""
Agent Compliance: missing mandatory, contradictions, disclaimers, next_question_id.
Rule-based; LLM can refine. Ne pas proposer une question déjà dans asked_questions / profile filled.
"""
from __future__ import annotations

import json
import os
from typing import Any

from ._llm import chat, load_prompt
from services.chatbot_epargne.questions.library import Q_PROJECT_TYPE


def run_compliance(
    profile: dict,
    product_matrix: list[dict] | None = None,
    asked_questions: list[str] | None = None,
    conversation_summary: str | None = None,
    conversation_facts: list[str] | None = None,
    llm: object | None = None,
) -> dict[str, Any]:
    """
    Returns: missing_mandatory[], contradictions[], disclaimer_ids_to_show[], next_suggested_question_id, warnings[].
    """
    asked = asked_questions or []
    payload = profile or {}
    project_type = payload.get("project_type")
    project_type_conf = payload.get("project_type_confidence")
    goal = payload.get("goal") or {}
    horizon_months = payload.get("horizon_months")
    horizon_bucket = payload.get("horizon_bucket")
    liquidity_raw = payload.get("liquidity_needs")
    if isinstance(liquidity_raw, dict):
        liquidity = (liquidity_raw.get("value") or "").lower()
    else:
        liquidity = (liquidity_raw or "").lower()
    risk = payload.get("risk_tolerance_score")
    loss_cap = (payload.get("loss_capacity") or "").lower()

    missing: list[str] = []
    if project_type is None or (project_type_conf is not None and float(project_type_conf) < 0.7):
        if Q_PROJECT_TYPE not in asked:
            missing.append("project_type")
    if not goal.get("type") and not goal.get("narrative"):
        missing.append("goal")
    if horizon_bucket is None and horizon_months is None:
        if "q_horizon" not in asked:
            missing.append("horizon_bucket")
    if risk is None:
        if "q_risk" not in asked:
            missing.append("risk_tolerance_score")

    contradictions: list[dict] = []
    # horizon court + produit illiquide 5 ans
    if horizon_months is not None and horizon_months < 60:
        if _profile_wants_illiquid(payload):
            contradictions.append({
                "type": "horizon_liquidity",
                "message": "Horizon inférieur à 5 ans incompatible avec un fonds bloqué 5 ans.",
                "repair_id": "repair_horizon",
            })

    disclaimers: list[str] = []
    if risk is not None and risk >= 5:
        disclaimers.append("volatility")
    disclaimers.append("non_advice")

    next_id = _pick_next(missing, asked, contradictions)
    warnings: list[str] = []

    # Optionally refine with LLM
    system = load_prompt("compliance")
    if system and (llm is not None or os.getenv("OPENAI_API_KEY")):
        summary_context = f"\nconversation_summary: {conversation_summary or '(aucun résumé)'}\nconversation_facts: {conversation_facts or []}\n" if conversation_summary or conversation_facts else ""
        user = (
            f"profile: {json.dumps(payload, ensure_ascii=False)}\n"
            f"asked_questions: {asked}\n"
            f"{summary_context}"
            f"missing_mandatory (rule-based): {missing}\n"
            f"contradictions (rule-based): {contradictions}\n\n"
            "Réponds en JSON: missing_mandatory, contradictions, disclaimer_ids_to_show, next_suggested_question_id, warnings."
            "Utilise le conversation_summary et conversation_facts pour éviter de reposer des questions déjà répondues."
        )
        out = (llm.chat(system, user, json_mode=True, temperature=0.1) if llm and hasattr(llm, "chat") else chat(system, user, json_mode=True, temperature=0.1))
        if out:
            try:
                data = json.loads(out)
                missing = data.get("missing_mandatory", missing)
                contradictions = data.get("contradictions", contradictions)
                disclaimers = data.get("disclaimer_ids_to_show", disclaimers)
                next_id = data.get("next_suggested_question_id") or next_id
                warnings = data.get("warnings", warnings)
            except json.JSONDecodeError:
                pass

    return {
        "missing_mandatory": missing,
        "contradictions": contradictions,
        "disclaimer_ids_to_show": disclaimers,
        "next_suggested_question_id": next_id,
        "warnings": warnings,
    }


def _profile_wants_illiquid(profile: dict) -> bool:
    # Placeholder: we don't have product_matrix in this call. Assume we detect from constraints/preferences.
    prefs = (profile.get("preferences") or []) + (profile.get("constraints") or [])
    low = " ".join(str(p).lower() for p in prefs)
    return "fonds 5" in low or "bloqué 5" in low or "illiquid" in low


def _pick_next(missing: list[str], asked: list[str], contradictions: list) -> str:
    if contradictions:
        r = (contradictions[0] or {}).get("repair_id")
        if r:
            return r
    if "project_type" in missing and Q_PROJECT_TYPE not in asked:
        return Q_PROJECT_TYPE
    if "goal" in missing and "q_goal" not in asked:
        return "q_goal"
    if "horizon_bucket" in missing and "q_horizon" not in asked:
        return "q_horizon"
    if "risk_tolerance_score" in missing and "q_risk" not in asked:
        return "q_risk"
    return "q_recap"
