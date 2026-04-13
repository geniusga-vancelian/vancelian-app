"""
Agent Portfolio: allocation DÉTERMINISTE (règles, pas de LLM pour les poids).
Retourne allocation vide si completeness < seuil. Pas de promesse de rendement.
"""
from __future__ import annotations

from typing import Any

_COMPLETENESS_THRESHOLD = 0.4  # 60s flow


def run_portfolio(
    profile: dict,
    product_universe: list[dict] | None = None,
    constraints: list[str] | None = None,
) -> dict[str, Any]:
    """
    Returns: { allocation: [{ instrument_id, weight_pct }], rationale, warnings, disclaimers }
    Tous les % viennent de règles, jamais du LLM.
    """
    comp = float(profile.get("completeness_score") or 0)
    if comp < _COMPLETENESS_THRESHOLD:
        return {
            "allocation": [],
            "rationale": "Profil encore incomplet pour une proposition. Répondez à quelques questions pour une première idée.",
            "warnings": [],
            "disclaimers": ["non_advice"],
        }

    horizon = profile.get("horizon_bucket") or profile.get("horizon_months")
    risk = profile.get("risk_tolerance_score")
    # Mapper risk 1–10 -> conservateur/équilibré/dynamique
    if risk is None:
        risk = 5
    if risk <= 3:
        bucket = "conservateur"
    elif risk <= 6:
        bucket = "équilibré"
    else:
        bucket = "dynamique"

    # Règles déterministes (blocs génériques, pas d’ISIN)
    if bucket == "conservateur":
        allocation = [
            {"instrument_id": "monetaire", "label": "Monétaire / Fonds euros", "weight_pct": 70},
            {"instrument_id": "obligataire", "label": "Obligataire", "weight_pct": 30},
        ]
        rationale = "Profil conservateur : priorité à la stabilité. Répartition indicative entre fonds euros et obligataire."
    elif bucket == "équilibré":
        allocation = [
            {"instrument_id": "monetaire", "label": "Monétaire / Fonds euros", "weight_pct": 30},
            {"instrument_id": "obligataire", "label": "Obligataire", "weight_pct": 40},
            {"instrument_id": "actions", "label": "Actions / UC", "weight_pct": 30},
        ]
        rationale = "Profil équilibré : mix stabilité et croissance. Répartition indicative. La part actions peut varier selon les marchés."
    else:
        allocation = [
            {"instrument_id": "monetaire", "label": "Monétaire / Fonds euros", "weight_pct": 10},
            {"instrument_id": "obligataire", "label": "Obligataire", "weight_pct": 30},
            {"instrument_id": "actions", "label": "Actions / UC", "weight_pct": 60},
        ]
        rationale = "Profil dynamique : part actions plus élevée. Volatilité plus importante. Répartition indicative."

    warnings = []
    if horizon == "short" or (isinstance(horizon, (int, float)) and horizon is not None and int(horizon) < 36):
        if any(a.get("instrument_id") == "actions" and (a.get("weight_pct") or 0) > 20 for a in allocation):
            warnings.append("Horizon court : la part actions est limitée par nos règles.")

    disclaimers = ["volatility", "non_advice"]
    if any(a.get("instrument_id") == "actions" for a in allocation):
        disclaimers = ["volatility", "non_advice"]

    return {
        "allocation": allocation,
        "rationale": rationale,
        "warnings": warnings,
        "disclaimers": disclaimers,
    }
