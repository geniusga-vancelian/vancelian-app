"""Portfolio engine (allocation rules) without AI."""
from typing import Dict, Any
from .schemas import ClientProfile


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _risk_score(tolerance_score: Any, knowledge_level: Any) -> int:
    base = _to_float(tolerance_score) or 5.0
    knowledge = str(knowledge_level or "").lower()
    if "début" in knowledge:
        base -= 1.0
    if "à l’aise" in knowledge or "aise" in knowledge or "avancé" in knowledge:
        base += 1.0
    return int(min(10, max(1, round(base))))


def _profile_label(score: int) -> str:
    if score <= 3:
        return "prudent"
    if score <= 6:
        return "equilibre"
    return "dynamique"


def build_portfolio(profile: ClientProfile) -> Dict[str, Any]:
    horizon_months = _to_float(profile.timeline.get("horizon_months"))
    tolerance_score = profile.risk.get("tolerance_score")
    knowledge_level = profile.knowledge_level
    liquidity = str(profile.capacity.get("liquidity") or "").lower()

    risk_score = _risk_score(tolerance_score, knowledge_level)
    label = _profile_label(risk_score)

    guardrails = []
    explanations = []

    if horizon_months and horizon_months < 12:
        allocation = {"core": 1.0, "satellite": 0.0}
        guardrails.append("short_term => no volatile assets")
        explanations.append("Horizon court : priorité à la stabilité et à la liquidité.")
    elif 12 <= horizon_months <= 36:
        if label == "prudent":
            allocation = {"core": 0.95, "satellite": 0.05}
        elif label == "equilibre":
            allocation = {"core": 0.85, "satellite": 0.15}
        else:
            allocation = {"core": 0.8, "satellite": 0.2}
        explanations.append("Horizon moyen : core majoritaire, satellite limité.")
    else:
        if label == "prudent":
            allocation = {"core": 0.85, "satellite": 0.15}
        elif label == "equilibre":
            allocation = {"core": 0.75, "satellite": 0.25}
        else:
            allocation = {"core": 0.6, "satellite": 0.4}
        explanations.append("Horizon long : satellite plus présent selon confort.")

    if "tout moment" in liquidity or "quotidien" in liquidity:
        guardrails.append("high_liquidity => keep core liquid")
        explanations.append("Besoin de liquidité élevé : core liquidité renforcée.")

    return {
        "profile_label": label,
        "risk_score": risk_score,
        "allocation": allocation,
        "guardrails": guardrails,
        "explanations": explanations,
    }
