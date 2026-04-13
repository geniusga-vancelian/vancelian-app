"""Next Question Selector (V1 refactor)
------------------------------------
Goal:
- Read the conversation questions JSON
- Select next question by project_type
- Confidence gating: never re-ask if already known with confidence >= threshold
- Intelligent fallback when project is vague/unknown or data missing
- Smooth transition to "create Vancelian savings vault" once enough info exists

Assumptions about `state` structure:
- state is a dict storing the session state / ClientProfile-like object
- state.get("answers", {}) contains confidence-tracked answers, by dot-path keys:
    answers["goal.type"] = {"value": "travel", "confidence": 0.9, ...}
    answers["goal.target_amount"] = {"value": 4500, "confidence": 0.92, ...}
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_THRESHOLD = 0.85


# ----------------------------
# Registry loading
# ----------------------------

def load_conversation_questions(path: str) -> Dict[str, Any]:
    """
    Load the JSON file (conversation_questions.json) and normalize into:
    {
      "travel": {"questions":[...], ...},
      "purchase": {"questions":[...], ...},
      "retirement": {"questions":[...], ...},
      ...
    }
    The JSON may be one object per file, a dict registry, or dict of lists.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Allow either list or dict
    if isinstance(data, list):
        registry: Dict[str, Any] = {}
        for item in data:
            pt = item.get("project_type")
            if not pt:
                continue
            registry[pt] = item
        return registry

    if isinstance(data, dict) and "project_type" in data:
        return {data["project_type"]: data}

    # Possibly already a registry
    return data


def load_default_registry() -> Dict[str, Any]:
    """
    Looks for env FINANCE_STRATEGY_QUESTIONS_JSON, otherwise defaults to a path
    relative to this file:
      api/services/finance_strategy_chat/conversation_questions.json
    """
    env_path = os.getenv("FINANCE_STRATEGY_QUESTIONS_JSON")
    if env_path and os.path.exists(env_path):
        return load_conversation_questions(env_path)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(base_dir, "conversation_questions.json")
    if os.path.exists(default_path):
        return load_conversation_questions(default_path)

    return {}


# ----------------------------
# Helpers: answers, confidence
# ----------------------------

def _ans_entry(state: Dict[str, Any], key: str) -> Dict[str, Any]:
    answers = state.get("answers") or {}
    return answers.get(key) or {}


def ans_value(state: Dict[str, Any], key: str) -> Any:
    entry = _ans_entry(state, key)
    return entry.get("value")


def ans_conf(state: Dict[str, Any], key: str, default: float = 0.0) -> float:
    entry = _ans_entry(state, key)
    try:
        return float(entry.get("confidence") or default)
    except Exception:
        return default


def is_known(state: Dict[str, Any], key: str, threshold: float = DEFAULT_THRESHOLD) -> bool:
    v = ans_value(state, key)
    if v is None or v == "" or v == "—":
        return False
    return ans_conf(state, key) >= threshold


def any_known(state: Dict[str, Any], keys: List[str], threshold: float = DEFAULT_THRESHOLD) -> bool:
    return any(is_known(state, k, threshold) for k in keys)


def all_known(state: Dict[str, Any], keys: List[str], threshold: float = DEFAULT_THRESHOLD) -> bool:
    return all(is_known(state, k, threshold) for k in keys)


# ----------------------------
# Project type normalization
# ----------------------------

PROJECT_TYPE_MAP = {
    "travel": {"travel", "voyage", "trip"},
    "purchase": {"purchase", "achat", "buy", "achat_plaisir"},
    "real_estate": {"real_estate", "immobilier", "house", "maison"},
    "retirement": {"retirement", "long_term", "retraite", "avenir", "future_family"},
    "safety": {"safety", "urgence", "emergency", "filet_securite"},
    "other": {"other", "autre"},
    "unknown": {"unknown", "none", "vague"},
}


def normalize_project_type(raw: Optional[str]) -> str:
    if not raw:
        return "unknown"
    r = str(raw).strip().lower()
    for canonical, synonyms in PROJECT_TYPE_MAP.items():
        if r in synonyms:
            return canonical
    if r in PROJECT_TYPE_MAP:
        return r
    return "other"


# ----------------------------
# Fallback questions (when JSON is missing / project vague)
# ----------------------------

FALLBACK_CLARIFY_PROJECT = {
    "step_id": "clarify_project",
    "question_text": (
        "🙂 OK. Dis-moi juste : tu veux rendre possible quoi avec cette épargne ?\n\n"
        "Un voyage, un achat, un projet de vie, un filet de sécurité… même si c’est flou, c’est parfait."
    ),
    "ui": {
        "type": "quick_replies",
        "allow_free_text": True,
        "quick_replies": [
            "✈️ Faire un voyage",
            "👜 Me faire plaisir (achat)",
            "🏡 Projet immobilier",
            "🌱 Construire l’avenir / retraite",
            "🛟 Me sentir plus serein(e)",
            "Autre",
        ],
    },
    "targets": ["goal.type", "goal.description"],
    "reason": "fallback: project_type unknown or unclear",
}

FALLBACK_COLLECT_BUDGET_STYLE = {
    "step_id": "collect_budget_style",
    "question_text": (
        "Pour qu’on avance vite et bien : tu as déjà une idée du budget,\n"
        "ou tu préfères qu’on l’estime ensemble ?"
    ),
    "ui": {
        "type": "quick_replies",
        "allow_free_text": True,
        "quick_replies": [
            "J’ai une idée du budget",
            "Aide-moi à estimer",
            "Je ne sais pas encore",
        ],
    },
    "targets": ["goal.target_amount"],
    "reason": "fallback: need target_amount or estimation path",
}

FALLBACK_COLLECT_HORIZON = {
    "step_id": "collect_horizon",
    "question_text": "📅 Tu aimerais que ce projet soit possible dans combien de temps, à peu près ?",
    "ui": {"type": "free_text", "allow_free_text": True},
    "targets": ["timeline.horizon_months"],
    "reason": "fallback: missing horizon",
}

FALLBACK_FUNDING_INITIAL = {
    "step_id": "funding_initial",
    "question_text": (
        "Pour construire un plan réaliste :\n"
        "tu penses pouvoir mettre une petite somme au départ, ou on démarre uniquement au mensuel ?"
    ),
    "ui": {
        "type": "quick_replies",
        "allow_free_text": True,
        "quick_replies": [
            "Uniquement au mensuel",
            "Je peux mettre une petite somme au départ",
            "Je ne sais pas encore",
        ],
    },
    "targets": ["goal.initial_contribution_amount"],
    "reason": "fallback: need initial funding preference/amount",
}

FALLBACK_FUNDING_MONTHLY = {
    "step_id": "funding_monthly",
    "question_text": "🔁 Et chaque mois, quel montant te semblerait confortable (sans te mettre en difficulté) ?",
    "ui": {"type": "free_text", "allow_free_text": True},
    "targets": ["capacity.monthly_contribution"],
    "reason": "fallback: missing monthly contribution",
}

FALLBACK_TRANSITION_VAULT = {
    "step_id": "offer_vault",
    "question_text": (
        "✅ Parfait. On a une base claire.\n\n"
        "**On crée un coffre d’épargne Vancelian dédié à ce projet**, et je te propose un plan simple "
        "que tu peux suivre sans stress.\n\n"
        "On y va ?"
    ),
    "ui": {
        "type": "quick_replies",
        "allow_free_text": True,
        "quick_replies": ["Oui, on crée le coffre", "Je veux d’abord relire le récap"],
    },
    "targets": ["action.create_vault"],
    "reason": "fallback: ready for vault transition",
}


# ----------------------------
# Readiness rules for vault transition (V1)
# ----------------------------

def ready_for_plan(state: Dict[str, Any], threshold: float = DEFAULT_THRESHOLD) -> bool:
    """
    Minimum viable set to propose "plan + create vault":
    - goal.type + goal.description known
    - horizon OR target_date known (for long_term it can be coarse)
    - monthly_contribution known (or at least a preference)
    """
    goal_ok = is_known(state, "goal.type", 0.75) and is_known(state, "goal.description", 0.60)
    horizon_ok = any_known(state, ["timeline.horizon_months", "timeline.target_date", "timeline.horizon_years"], 0.70)
    monthly_ok = is_known(state, "capacity.monthly_contribution", 0.75)

    pt = normalize_project_type(ans_value(state, "goal.type"))
    if pt in ("travel", "purchase", "real_estate"):
        target_ok = is_known(state, "goal.target_amount", 0.75)
        return goal_ok and horizon_ok and monthly_ok and target_ok

    return goal_ok and horizon_ok and monthly_ok


# ----------------------------
# Choose next question from registry
# ----------------------------

def _question_is_covered(state: Dict[str, Any], targets: List[str], threshold: float = DEFAULT_THRESHOLD) -> bool:
    if not targets:
        return False
    return all_known(state, targets, threshold)


def _pick_first_uncovered_from_registry(
    state: Dict[str, Any],
    registry: Dict[str, Any],
    project_type: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> Optional[Dict[str, Any]]:
    pt_entry = registry.get(project_type)
    if not pt_entry:
        return None

    questions = pt_entry.get("questions") if isinstance(pt_entry, dict) else pt_entry
    if not questions:
        return None

    for q in questions:
        targets = q.get("targets") or q.get("expected_fields") or []
        if not _question_is_covered(state, targets, threshold):
            ui = {
                "type": "quick_replies" if q.get("suggestions") else "free_text",
                "allow_free_text": True,
                "quick_replies": q.get("suggestions"),
            }
            return {
                "step_id": q.get("id"),
                "question_text": q.get("text"),
                "ui": ui,
                "targets": targets,
                "reason": f"registry:{project_type} first uncovered question",
            }
    return None


def choose_next_question(
    state: Dict[str, Any],
    registry: Dict[str, Any],
    threshold: float = DEFAULT_THRESHOLD,
) -> Dict[str, Any]:
    """
    Decision order:
    1) If project unclear -> clarify project (fallback)
    2) If registry has questions for project_type -> pick first uncovered
    3) If missing critical fields -> fallback questions (budget/horizon/funding)
    4) If ready -> transition to vault
    """
    pt = normalize_project_type(ans_value(state, "goal.type"))
    type_known = is_known(state, "goal.type", 0.75)
    blocked_steps = {"project_hint", "cadre_simple", "objectifs_epargne", "clarify_project"}

    clarity = ans_value(state, "project_clarity")
    clarity_conf = ans_conf(state, "project_clarity")
    desc = ans_value(state, "goal.description")
    desc_conf = ans_conf(state, "goal.description")

    project_clear = False
    if clarity and str(clarity).lower() in ("clear", "clair"):
        project_clear = clarity_conf >= 0.60
    elif desc and desc_conf >= 0.60 and pt != "unknown":
        project_clear = True

    if (not project_clear or pt == "unknown") and not type_known:
        return FALLBACK_CLARIFY_PROJECT

    if ready_for_plan(state, threshold=threshold):
        return FALLBACK_TRANSITION_VAULT

    from_registry = _pick_first_uncovered_from_registry(state, registry, pt, threshold=threshold)
    if from_registry:
        return from_registry

    if not is_known(state, "goal.target_amount", 0.75) and pt in ("travel", "purchase", "real_estate"):
        return FALLBACK_COLLECT_BUDGET_STYLE

    if not any_known(state, ["timeline.horizon_months", "timeline.target_date", "timeline.horizon_years"], 0.70):
        return FALLBACK_COLLECT_HORIZON

    if not is_known(state, "goal.initial_contribution_amount", 0.75):
        return FALLBACK_FUNDING_INITIAL

    if not is_known(state, "capacity.monthly_contribution", 0.75):
        return FALLBACK_FUNDING_MONTHLY

    candidate = FALLBACK_TRANSITION_VAULT
    if type_known and candidate.get("step_id") in blocked_steps:
        return FALLBACK_TRANSITION_VAULT
    return candidate


if __name__ == "__main__":
    registry = load_default_registry()
    state = {
        "answers": {
            "goal.type": {"value": "travel", "confidence": 0.9},
            "goal.description": {"value": "Voyage à New York", "confidence": 0.8},
            "timeline.horizon_months": {"value": 6, "confidence": 0.7},
        }
    }
    print(choose_next_question(state, registry))
