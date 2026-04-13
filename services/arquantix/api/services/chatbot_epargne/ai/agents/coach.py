"""
Agent Coach: user-facing questions, reformulation, empathie. Pas de chiffres de performance.
Textes fixes pour Q_BUDGET_MODE, Q_TARGET_AMOUNT, Q_RISK_CALIB, Q_LIQUIDITY (prompts 2–4).
"""
from __future__ import annotations

import math

from ._llm import chat, load_prompt

# Messages exacts (prompts 2–4) : Budget, Objectif total, Risque, Liquidité
_QUESTION_Q_BUDGET_MODE = """Parfait 👍
Pour préparer ce projet, tu préfères plutôt :

A) Mettre un petit montant chaque mois
B) Mettre un montant au départ
C) Combiner les deux

Dis-moi simplement A, B ou C (ou explique avec tes mots)."""

_QUESTION_Q_TARGET_AMOUNT = """Tu as déjà une idée du budget total pour ce projet ?

Par exemple :
• 2 000 €
• 5 000 €
• 10 000 €
• ou « je ne sais pas encore »

Il n'y a pas de mauvaise réponse — on peut ajuster ensuite."""

_QUESTION_Q_RISK_CALIB = """Dernière question pour adapter la stratégie 👌

Si la valeur de ton épargne baissait temporairement de 5 à 10%, tu serais plutôt :

A) OK si c'est temporaire
B) Plutôt stressé, je préfère quelque chose de très stable
C) Je ne sais pas trop

Choisis ce qui te ressemble le plus."""

_QUESTION_Q_LIQUIDITY = "Auriez-vous besoin de récupérer tout ou partie de cette épargne rapidement ?"
_QUESTION_Q_BUDGET_SINGLE = "Tu pourrais plutôt mettre quelque chose au départ, mettre un peu régulièrement, ou les deux ?"
_QUESTION_Q_TIME_OR_BUDGET = "Laquelle te paraît la plus confortable ? (6 / 12 / 24 mois)"
_QUESTION_Q_PROJECT_TYPE_OPEN = (
    "Bonjour 🙂\n"
    "Parle-moi librement de ton projet d’épargne.\n"
    "Je vais t’aider à le clarifier et à le construire pas à pas."
)
_QUESTION_Q_PROJECT_TYPE_CLARIFY = "Merci. Dis-moi simplement ce que tu veux rendre possible, en quelques mots."
_QUESTION_Q_GOAL_FREE = "D’accord 🙂 Dis-moi en une phrase ce que tu veux rendre possible grâce à ton épargne."
_QUESTION_Q_GOAL_CLARIFY = (
    "Je ne suis pas sûr d’avoir bien compris. Tu peux reformuler en une phrase ?\n"
    "Exemples : “acheter un sac”, “finir le mois plus sereinement”, “préparer la retraite”, "
    "“épargner pour mes enfants”, “préparer un voyage”, “faire fructifier mon argent”."
)
_QUESTION_Q_GOAL_FORCE_PICK = (
    "Je n’arrive pas à identifier précisément ton projet pour l’instant.\n"
    "Pour m’aider, choisis simplement la catégorie qui correspond le mieux 👇"
)
_QUESTION_Q_PROJECT_DETAILS = "Tu penses à quoi exactement ?"

_PROJECT_TYPE_HYPOTHESES = {
    "buy_something": (
        "te faire plaisir sur un achat précis",
        "un achat précis",
        "te donner plus de liberté au quotidien",
    ),
    "live_better": (
        "être plus à l’aise au quotidien",
        "mieux vivre au quotidien",
        "préparer un achat précis",
    ),
    "prepare_future": (
        "préparer l’avenir",
        "préparer l’avenir",
        "te faire plaisir avec un achat",
    ),
    "protect_family": (
        "protéger ou aider tes proches",
        "aider/protéger tes proches",
        "préparer ton avenir personnel",
    ),
    "experiences": (
        "vivre une expérience marquante",
        "une expérience (voyage, projet perso)",
        "améliorer ton quotidien",
    ),
    "grow_money": (
        "faire fructifier ton argent",
        "faire fructifier ton argent",
        "financer un projet précis",
    ),
}


def _build_project_type_probe(profile_partial: dict) -> str:
    ptype = profile_partial.get("project_type")
    hypothesis, option_a, option_b = _PROJECT_TYPE_HYPOTHESES.get(
        ptype,
        ("rendre possible un projet qui compte pour toi", "un achat précis", "mieux vivre au quotidien"),
    )
    return (
        f"Si je comprends bien, tu aimerais {hypothesis}.\n"
        f"Est-ce que tu penses plutôt à {option_a} ou à {option_b} ?"
    )


def _build_horizon_options(profile_partial: dict) -> str | None:
    goal = profile_partial.get("goal") or {}
    target_amount = goal.get("target_amount") or profile_partial.get("target_amount")
    if target_amount is None:
        return None
    try:
        target_amount = float(target_amount)
    except (TypeError, ValueError):
        return None
    initial_amount = profile_partial.get("initial_amount") or 0
    try:
        initial_amount = float(initial_amount)
    except (TypeError, ValueError):
        initial_amount = 0
    base = max(target_amount - initial_amount, 0)
    months_options = [6, 12, 24]
    monthly = {m: int(math.ceil(base / m)) for m in months_options}
    return (
        "Pas de souci 🙂 Voici trois options simples :\n"
        f"• 6 mois : {monthly[6]} €/mois\n"
        f"• 12 mois : {monthly[12]} €/mois\n"
        f"• 24 mois : {monthly[24]} €/mois\n"
        "(on pourra ajuster à la baisse si tu préfères)\n\n"
        "Laquelle te paraît la plus confortable ? (6 / 12 / 24 mois)"
    )


def get_question_text(next_question_id: str | None) -> str:
    """
    Retourne le message utilisateur exact pour une question ID.
    Utilisé par l'orchestrator pour show_project_summary (résumé + question) et fallback coach.
    """
    if not next_question_id:
        return "Pouvez-vous m'en dire un peu plus ?"
    if next_question_id in ("Q_BUDGET_MODE", "q_budget"):
        return _QUESTION_Q_BUDGET_MODE
    if next_question_id in ("Q_TARGET_AMOUNT", "q_goal"):
        return _QUESTION_Q_TARGET_AMOUNT
    if next_question_id in ("Q_RISK_CALIB", "q_risk"):
        return _QUESTION_Q_RISK_CALIB
    if next_question_id in ("Q_LIQUIDITY", "q_liquidity"):
        return _QUESTION_Q_LIQUIDITY
    if next_question_id == "q_budget_single":
        return _QUESTION_Q_BUDGET_SINGLE
    if next_question_id == "q_horizon":
        return "Pour vous, c'est plutôt court (moins de 3 ans), moyen (3–7 ans) ou long (plus de 7 ans) ?"
    if next_question_id == "q_time_or_budget":
        return _QUESTION_Q_TIME_OR_BUDGET
    if next_question_id == "Q_PROJECT_TYPE":
        return _QUESTION_Q_PROJECT_TYPE_OPEN
    if next_question_id == "Q_GOAL_FREE":
        return _QUESTION_Q_GOAL_FREE
    if next_question_id == "Q_GOAL_CLARIFY":
        return _QUESTION_Q_GOAL_CLARIFY
    if next_question_id == "Q_GOAL_FORCE_PICK":
        return _QUESTION_Q_GOAL_FORCE_PICK
    if next_question_id == "Q_PROJECT_DETAILS":
        return _QUESTION_Q_PROJECT_DETAILS
    return "Pouvez-vous m'en dire un peu plus ?"


def run_coach(
    user_message: str,
    profile_partial: dict,
    suggested_questions: list[str],
    flow_stage: str,
    next_question_id: str | None = None,
    conversation_summary: str | None = None,
    conversation_facts: list[str] | None = None,
    llm: "LLMProtocol | None" = None,
) -> str:
    if next_question_id == "Q_PROJECT_TYPE":
        return _QUESTION_Q_PROJECT_TYPE_OPEN
    if next_question_id == "Q_GOAL_FREE":
        return _QUESTION_Q_GOAL_FREE
    if next_question_id == "Q_GOAL_CLARIFY":
        return _QUESTION_Q_GOAL_CLARIFY
    if next_question_id == "Q_GOAL_FORCE_PICK":
        return _QUESTION_Q_GOAL_FORCE_PICK
    if next_question_id == "Q_PROJECT_DETAILS":
        return _QUESTION_Q_PROJECT_DETAILS
    if next_question_id == "q_time_or_budget":
        return _build_horizon_options(profile_partial) or _QUESTION_Q_TIME_OR_BUDGET
    system = load_prompt("coach")
    summary_context = f"\nconversation_summary: {conversation_summary or '(aucun résumé)'}\nconversation_facts: {conversation_facts or []}\n" if conversation_summary or conversation_facts else ""
    user = (
        f"user_message: {user_message!r}\n"
        f"profile_partial: {profile_partial}\n"
        f"{summary_context}"
        f"suggested_questions: {suggested_questions}\n"
        f"flow_stage: {flow_stage}\n"
        f"next_question_id: {next_question_id or ''}\n\n"
        "Génère le message assistant (texte uniquement, en français)."
        "Utilise le conversation_summary et conversation_facts pour éviter de reposer des questions déjà répondues et adapter ton ton."
    )
    out = (llm.chat(system, user, json_mode=False, temperature=0.5) if llm else chat(system, user, json_mode=False, temperature=0.5))
    if not out or not out.strip():
        return _fallback_coach(flow_stage, next_question_id)
    return out.strip()


def _fallback_coach(flow_stage: str, next_question_id: str | None) -> str:
    if flow_stage == "welcome":
        return "Bonjour. En une phrase, quel est pour vous l’objectif de cette épargne ?"
    if flow_stage == "restitution":
        return "Voici une première idée d’allocation adaptée à votre projet. Il s’agit d’une illustration pédagogique, pas d’un conseil. Les performances passées ne préjugent pas des futures."
    if flow_stage == "show_project_summary":
        return get_question_text(next_question_id)
    return get_question_text(next_question_id)
