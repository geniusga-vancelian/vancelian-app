"""
Conversation Orchestrator (décision uniquement): action + next_question_id + reason.
Implémentation déterministe des règles system_orchestrator.md.
Ne parle pas à l'utilisateur. Pas d'allocation ni de % tant que mini-profil incomplet.
"""
from __future__ import annotations

from typing import Any

from services.chatbot_epargne.questions.library import (
    Q_GOAL_FREE,
    Q_GOAL_CLARIFY,
    Q_GOAL_FORCE_PICK,
    Q_PROJECT_DETAILS,
)

# IDs de questions (priorité: a) budget, b) objectif total, c) risque, d) liquidité)
Q_BUDGET_MODE = "Q_BUDGET_MODE"
Q_TARGET_AMOUNT = "Q_TARGET_AMOUNT"
Q_RISK_CALIB = "Q_RISK_CALIB"
Q_LIQUIDITY = "Q_LIQUIDITY"
Q_BUDGET_SINGLE = "q_budget_single"

ACTION_ASK = "ask_next_question"
ACTION_PROJECT_SUMMARY = "show_project_summary"
ACTION_STRATEGY_SUMMARY = "show_strategy_summary"
ACTION_GOAL_DONE = "goal_done"


def _get_goal(profile: dict) -> dict:
    g = profile.get("goal")
    return g if isinstance(g, dict) else {}


def _has(v: Any) -> bool:
    return v is not None and v != ""

def _confidence_ok(value: Any, confidence: Any) -> bool:
    if value is None:
        return False
    if confidence is None:
        return True
    try:
        return float(confidence) >= 0.7
    except (TypeError, ValueError):
        return False

def _needs_budget(profile: dict) -> bool:
    initial_ok = _confidence_ok(profile.get("initial_amount"), profile.get("initial_amount_confidence"))
    monthly_ok = _confidence_ok(profile.get("monthly_contribution"), profile.get("monthly_contribution_confidence"))
    return not (initial_ok and monthly_ok)

def _goal_confidence(profile: dict) -> float | None:
    conf = profile.get("goal_confidence")
    if conf is None:
        conf = profile.get("project_type_confidence")
    try:
        return float(conf) if conf is not None else None
    except (TypeError, ValueError):
        return None


def _goal_locked(profile: dict) -> bool:
    if profile.get("goal_locked") is True:
        return True
    conf = _goal_confidence(profile)
    if conf is None:
        return False
    return conf >= 0.7


def compute_goal_phase(profile: dict, turn_index: int | None) -> str | None:
    if (turn_index or 0) == 0:
        return None
    if _goal_locked(profile):
        return None
    attempts = int(profile.get("goal_attempts") or 0)
    if attempts <= 0:
        return "goal_free"
    if attempts == 1:
        return "goal_clarify"
    return "goal_force_pick"
def _liquidity_value_conf(profile: dict) -> tuple[Any, Any]:
    raw = profile.get("liquidity_needs")
    if isinstance(raw, dict):
        return raw.get("value"), raw.get("confidence")
    return raw, None

def _liquidity_conf_ok(profile: dict) -> bool:
    value, confidence = _liquidity_value_conf(profile)
    if value is None or value == "":
        return False
    if confidence is None:
        return True
    try:
        return float(confidence) >= 0.7
    except (TypeError, ValueError):
        return False


def can_show_allocation(profile: dict) -> bool:
    """
    Vrai ssi : goal.description, horizon_months, (target|monthly|initial), risk_tolerance_score.
    Tant que faux : ne jamais montrer d'allocation ni de %.
    """
    goal = _get_goal(profile)
    goal_ok = _has(goal.get("description")) or _has(goal.get("narrative")) or _has(goal.get("type"))
    horizon_ok = profile.get("horizon_months") is not None
    amount_ok = (
        _has(goal.get("target_amount")) or _has(profile.get("target_amount"))
        or _has(profile.get("monthly_contribution"))
        or _has(profile.get("initial_amount"))
    )
    risk_ok = profile.get("risk_tolerance_score") is not None
    return bool(goal_ok and horizon_ok and amount_ok and risk_ok)


def run_decide(
    investor_profile: dict,
    last_user_message: str,  # pylint: disable=unused-argument
    asked_questions: list[str],  # pylint: disable=unused-argument
    completeness_score: float,  # pylint: disable=unused-argument
    turn_index: int | None = None,
) -> dict[str, Any]:
    """
    Retourne: { "action", "next_question_id", "reason" }
    Règle 1: pas d'allocation/% tant que goal.description, horizon_months,
    (target_amount|monthly_contribution|initial_amount), risk_tolerance_score non remplis.
    Ordre priorité: a) budget, b) objectif total, c) risque, d) liquidité.
    """
    profile = investor_profile or {}
    goal = _get_goal(profile)

    if (turn_index or 0) == 0:
        return {
            "action": ACTION_ASK,
            "next_question_id": None,
            "goal_phase": None,
            "reason": "Ouverture UI-only, pas de question backend.",
        }

    if _goal_locked(profile):
        return {
            "action": ACTION_GOAL_DONE,
            "next_question_id": None,
            "goal_phase": None,
            "reason": "Étape GOAL atteinte : arrêt après résumé.",
        }

    goal_phase = compute_goal_phase(profile, turn_index)
    if goal_phase:
        next_q = {
            "goal_free": Q_GOAL_FREE,
            "goal_clarify": Q_GOAL_CLARIFY,
            "goal_force_pick": Q_GOAL_FORCE_PICK,
        }[goal_phase]
        return {
            "action": ACTION_ASK,
            "next_question_id": next_q,
            "goal_phase": goal_phase,
            "reason": f"Phase GOAL: {goal_phase}.",
        }

    goal_ok = _has(goal.get("description")) or _has(goal.get("narrative")) or _has(goal.get("type"))
    goal_desc_ok = _has(goal.get("description")) or _has(goal.get("narrative"))
    horizon_ok = profile.get("horizon_months") is not None
    budget_ok = _has(profile.get("monthly_contribution")) or _has(profile.get("initial_amount"))
    target_ok = _has(goal.get("target_amount")) or _has(profile.get("target_amount"))
    risk_ok = profile.get("risk_tolerance_score") is not None
    liquidity_ok = _liquidity_conf_ok(profile)
    budget_attempts = int(profile.get("budget_question_attempts") or 0)
    liquidity_attempts = int(profile.get("liquidity_question_attempts") or 0)
    needs_budget = _needs_budget(profile)

    amount_ok = target_ok or budget_ok

    mini_profile_complete = can_show_allocation(profile)
    project_summary_ready = goal_ok and horizon_ok and amount_ok

    should_ask_budget_single = (
        goal_desc_ok
        and target_ok
        and horizon_ok
        and needs_budget
        and budget_attempts < 2
    )

    budget_conf_ok = (
        _confidence_ok(profile.get("initial_amount"), profile.get("initial_amount_confidence"))
        or _confidence_ok(profile.get("monthly_contribution"), profile.get("monthly_contribution_confidence"))
    )
    liquidity_should_ask = goal_desc_ok and horizon_ok and budget_conf_ok and not liquidity_ok and liquidity_attempts < 2

    def _next_missing() -> str | None:
        # a) budget, b) objectif total, c) risque, d) liquidité
        if not budget_ok:
            return Q_BUDGET_MODE
        if not target_ok:
            return Q_TARGET_AMOUNT
        if not risk_ok:
            return Q_RISK_CALIB
        if liquidity_should_ask:
            return Q_LIQUIDITY
        return None

    def _next_after_project() -> str | None:
        if not risk_ok:
            return Q_RISK_CALIB
        if liquidity_should_ask:
            return Q_LIQUIDITY
        return None

    if mini_profile_complete:
        return {
            "action": ACTION_STRATEGY_SUMMARY,
            "next_question_id": None,
            "goal_phase": None,
            "reason": "Mini-profil complet : goal.description, horizon, montant et risque renseignés.",
        }
    if should_ask_budget_single:
        return {
            "action": ACTION_ASK,
            "next_question_id": Q_BUDGET_SINGLE,
            "goal_phase": None,
            "reason": "Collecte budget (montant initial et/ou régulier) en une question.",
        }
    if project_summary_ready:
        nq = _next_after_project()
        return {
            "action": ACTION_PROJECT_SUMMARY,
            "next_question_id": nq,
            "goal_phase": None,
            "reason": "Projet cadré (objectif, horizon, budget). Il manque risque ou liquidité.",
        }
    nq = _next_missing()
    return {
        "action": ACTION_ASK,
        "next_question_id": nq,
        "goal_phase": None,
        "reason": "Champ(s) manquant(s) : priorité budget, objectif total, risque, liquidité.",
    }
