"""
Agent Summarizer: génère/maintient un résumé conversationnel (2-6 lignes) + facts list.
Évite les répétitions en donnant un contexte narratif aux autres agents.
"""
from __future__ import annotations

import json
from typing import Any

from ._llm import chat, load_prompt


def run_summarizer(
    previous_summary: str | None,
    last_turns: list[dict[str, str]],
    current_profile: dict,
    llm: "LLMProtocol | None" = None,
) -> dict[str, Any]:
    """
    Génère un résumé conversationnel mis à jour.

    Args:
        previous_summary: Résumé précédent (peut être None au premier tour)
        last_turns: Liste des derniers échanges [{"role": "user|assistant", "content": "..."}]
        current_profile: Profil JSON actuel (InvestorProfile)
        llm: Client LLM optionnel

    Returns:
        {
            "summary": "2-6 lignes max",
            "facts": ["fait 1", "fait 2", ...],
            "open_points": ["ce qui manque", ...]
        }
    """
    system = load_prompt("summarizer")
    if not system:
        # Fallback heuristique si pas de prompt
        return _heuristic_summary(previous_summary, last_turns, current_profile)

    # Construire le contexte pour le LLM
    profile_json = json.dumps(current_profile, ensure_ascii=False, indent=2)
    turns_text = "\n".join([f"{t.get('role', 'unknown')}: {t.get('content', '')}" for t in last_turns[-10:]])  # Max 10 derniers tours

    user = f"""previous_summary: {previous_summary or "(aucun résumé précédent)"}

last_turns:
{turns_text}

current_profile:
{profile_json}

Génère le résumé mis à jour au format JSON strict."""
    out = (llm.chat(system, user, json_mode=True, temperature=0.2) if llm else chat(system, user, json_mode=True, temperature=0.2))
    
    if not out or not out.strip():
        return _heuristic_summary(previous_summary, last_turns, current_profile)
    
    try:
        parsed = json.loads(out)
        return {
            "summary": parsed.get("summary", ""),
            "facts": parsed.get("facts", []),
            "open_points": parsed.get("open_points", []),
        }
    except json.JSONDecodeError:
        return _heuristic_summary(previous_summary, last_turns, current_profile)


def _heuristic_summary(
    previous_summary: str | None,
    last_turns: list[dict[str, str]],
    current_profile: dict,
) -> dict[str, Any]:
    """
    Fallback heuristique si LLM indisponible ou erreur.
    Extrait les faits du profil et construit un résumé basique.
    """
    facts: list[str] = []
    open_points: list[str] = []

    def _append_unique(target: list[str], value: str) -> None:
        if value and value not in target:
            target.append(value)
    
    # Extraire les faits du profil
    goal = current_profile.get("goal") or {}
    if goal.get("type") or goal.get("narrative"):
        desc = goal.get("narrative") or goal.get("type") or goal.get("description") or ""
        if desc:
            _append_unique(facts, f"Projet: {desc}")
    else:
        _append_unique(open_points, "Objectif du projet")
    
    horizon = current_profile.get("horizon_months") or current_profile.get("horizon_bucket")
    if horizon is not None:
        if isinstance(horizon, (int, float)):
            _append_unique(facts, f"Horizon: {int(horizon)} mois")
        else:
            _append_unique(facts, f"Horizon: {horizon}")
    else:
        _append_unique(open_points, "Horizon d'épargne")
    
    target = goal.get("target_amount") or current_profile.get("target_amount")
    if target is not None:
        _append_unique(facts, f"Objectif total: {int(target)} €")
    else:
        _append_unique(open_points, "Montant cible")
    
    monthly = current_profile.get("monthly_contribution")
    if monthly is not None:
        _append_unique(facts, f"Effort mensuel: {int(monthly)} €")
    else:
        _append_unique(open_points, "Montant mensuel")
    
    risk = current_profile.get("risk_tolerance_score")
    if risk is not None:
        _append_unique(facts, f"Risque: {risk}")
    else:
        _append_unique(open_points, "Tolérance au risque")

    project_type = current_profile.get("project_type")
    project_type_conf = current_profile.get("goal_confidence")
    if project_type_conf is None:
        project_type_conf = current_profile.get("project_type_confidence")
    try:
        project_type_conf = float(project_type_conf) if project_type_conf is not None else None
    except (TypeError, ValueError):
        project_type_conf = None

    project_type_labels = {
        "buy_something": "Acheter quelque chose",
        "live_better": "Mieux vivre au quotidien",
        "prepare_future": "Préparer mon avenir",
        "protect_family": "Protéger mes proches",
        "experiences": "Vivre des expériences",
        "grow_money": "Faire fructifier mon argent",
        "other": "Autre",
    }
    project_type_sentence = None
    if project_type and project_type_conf is not None and project_type_conf >= 0.7:
        label = project_type_labels.get(str(project_type), "Autre")
        _append_unique(facts, f"Catégorie projet : {label}")
        project_type_sentence = f"Le projet correspond à la catégorie : {label}."
    else:
        _append_unique(open_points, "Catégorie du projet à clarifier")

    liquidity = current_profile.get("liquidity_needs") or {}
    liquidity_value = liquidity.get("value") if isinstance(liquidity, dict) else None
    liquidity_conf = liquidity.get("confidence") if isinstance(liquidity, dict) else None
    try:
        liquidity_conf = float(liquidity_conf) if liquidity_conf is not None else None
    except (TypeError, ValueError):
        liquidity_conf = None

    liquidity_fact_map = {
        "low": "Souplesse souhaitée : faible (pas de retrait prévu)",
        "medium": "Souplesse souhaitée : moyenne (retrait possible si besoin)",
        "high": "Souplesse souhaitée : élevée (besoin de retrait possible)",
    }
    liquidity_sentence_map = {
        "low": "Il préfère laisser l’épargne intacte jusqu’à l’objectif final.",
        "medium": "Il souhaite garder une certaine souplesse pendant le projet.",
        "high": "Il souhaite pouvoir retirer une partie de l’épargne en cas de besoin.",
    }

    liquidity_sentence = None
    if liquidity_value in liquidity_fact_map and (liquidity_conf is not None and liquidity_conf >= 0.7):
        _append_unique(facts, liquidity_fact_map[liquidity_value])
        liquidity_sentence = liquidity_sentence_map.get(liquidity_value)
    else:
        _append_unique(open_points, "Besoin de retrait en cours de projet à clarifier")
    
    # Construire un résumé basique
    if previous_summary:
        summary = previous_summary
        if liquidity_sentence:
            lowered = summary.lower()
            if "souplesse" not in lowered and "retirer" not in lowered and "épargne intacte" not in lowered:
                summary = f"{summary} {liquidity_sentence}"
        if project_type_sentence:
            lowered = summary.lower()
            if "catégorie" not in lowered:
                summary = f"{summary} {project_type_sentence}"
    else:
        summary_parts = []
        if facts:
            summary_parts.append("L'utilisateur a commencé à définir son projet d'épargne.")
        else:
            summary_parts.append("Début de conversation.")
        if liquidity_sentence:
            summary_parts.append(liquidity_sentence)
        if project_type_sentence:
            summary_parts.append(project_type_sentence)
        summary = " ".join(summary_parts)
    
    return {
        "summary": summary,
        "facts": facts,
        "open_points": open_points,
    }
