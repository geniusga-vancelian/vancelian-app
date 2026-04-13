"""
Agent Copywriter: format restitution (one-screen/ELI12/savvy) + disclaimer_block.
Résumé Projet (avant stratégie) et Restitution Stratégie (prompt 6).
Aucun chiffre de rendement futur.
"""
from __future__ import annotations

import json
import os
from typing import Any

from ._llm import chat, load_prompt


def _risk_label(score: float | None) -> str:
    if score is None:
        return "à préciser"
    if score <= 3:
        return "Très stable"
    if score <= 5:
        return "Équilibré"
    return "Accepte les variations"


def run_copywriter_project_summary(
    profile: dict,
    conversation_summary: str | None = None,
    conversation_facts: list[str] | None = None,
) -> str:
    """
    Résumé Projet (prompt 5) : AVANT stratégie, sans allocation ni %.
    Carte live update. Format exact du prompt.
    """
    goal = profile.get("goal") or {}
    desc = goal.get("description") or goal.get("narrative") or goal.get("type") or "à définir"
    horizon = profile.get("horizon_months")
    horizon_s = f"{horizon} mois" if isinstance(horizon, (int, float)) else (horizon or "à définir")
    target = goal.get("target_amount") or profile.get("target_amount")
    target_s = f"{int(target):,} €".replace(",", "\u202f") if isinstance(target, (int, float)) else "à définir"
    monthly = profile.get("monthly_contribution")
    monthly_s = f"{int(monthly):,} €".replace(",", "\u202f") if isinstance(monthly, (int, float)) else "à définir"
    risk_s = _risk_label(profile.get("risk_tolerance_score"))

    return f"""### Ton projet, en résumé

• **Projet** : {desc}
• **Horizon** : {horizon_s}
• **Objectif total** : {target_s}
• **Effort mensuel** : {monthly_s}
• **Niveau de risque** : {risk_s}

👉 Il me manque encore 1 ou 2 infos pour te proposer une stratégie adaptée."""


# Restitution Stratégie (prompt 6) : uniquement quand can_show_allocation. Allocation dans un autre écran/step.
_STRATEGY_INTRO = """### Proposition de stratégie (indicative)

Compte tenu de :
• ton horizon
• ton objectif
• ton niveau de confort face aux variations

Une approche prudente et progressive peut être envisagée.

ℹ️ Cette répartition est une illustration pédagogique.
La valeur des investissements peut varier à la hausse comme à la baisse.
Il ne s'agit pas d'un conseil personnalisé."""


def run_copywriter(
    allocation: list[dict],
    rationale: str | None,
    profile: dict,
    format: str = "summary",
    disclaimer_ids: list[str] | None = None,
    conversation_summary: str | None = None,
    conversation_facts: list[str] | None = None,
    llm: object | None = None,
) -> dict[str, Any]:
    """
    Returns: { summary_text, disclaimer_block }
    format=strategy_intro : prompt 6, sans % d'allocation dans le texte (détails dans un autre écran/step).
    """
    if format == "strategy_intro":
        return {
            "summary_text": _STRATEGY_INTRO,
            "disclaimer_block": "Cette répartition est une illustration pédagogique. La valeur des investissements peut varier. Il ne s'agit pas d'un conseil personnalisé.",
        }

    blocks = [f"{a.get('label', a.get('instrument_id', '?'))}: {a.get('weight_pct', 0)}%" for a in (allocation or [])]
    text = " ; ".join(blocks) if blocks else "Répartition indicative non déterminée."
    summary = f"Une répartition indicative pourrait être : {text}. Cette répartition est une illustration pédagogique, pas un conseil personnalisé. Les performances passées ne préjugent pas des futures. La valeur de l'investissement peut baisser."
    disclaimer_block = "Les marchés peuvent varier. La valeur de votre investissement peut baisser. Il s'agit d'une illustration pédagogique, pas d'un conseil personnalisé."

    system = load_prompt("copywriter")
    if system and (llm is not None or os.getenv("OPENAI_API_KEY")):
        summary_context = f"\nconversation_summary: {conversation_summary or '(aucun résumé)'}\nconversation_facts: {conversation_facts or []}\n" if conversation_summary or conversation_facts else ""
        user = (
            f"allocation: {json.dumps(allocation or [], ensure_ascii=False)}\n"
            f"rationale: {rationale or ''}\n"
            f"profile (résumé): horizon={profile.get('horizon_bucket')}, risk={profile.get('risk_tolerance_score')}\n"
            f"{summary_context}"
            f"format: {format}\n"
            f"disclaimer_ids: {disclaimer_ids or []}\n\n"
            "Réponds en JSON: summary_text, disclaimer_block. Aucun chiffre de rendement futur."
        )
        out = (llm.chat(system, user, json_mode=True, temperature=0.3) if llm and hasattr(llm, "chat") else chat(system, user, json_mode=True, temperature=0.3))
        if out:
            try:
                data = json.loads(out)
                summary = (data.get("summary_text") or summary).strip()
                disclaimer_block = (data.get("disclaimer_block") or disclaimer_block).strip()
            except json.JSONDecodeError:
                pass

    # Hard guard: remove any phrase that looks like a future return
    for bad in [" vous gagnerez ", " garanti ", " % assuré ", " rendement garanti "]:
        if bad in summary.lower():
            summary = summary.replace(bad, " ")
        if bad in disclaimer_block.lower():
            disclaimer_block = disclaimer_block.replace(bad, " ")
    return {"summary_text": summary, "disclaimer_block": disclaimer_block}
