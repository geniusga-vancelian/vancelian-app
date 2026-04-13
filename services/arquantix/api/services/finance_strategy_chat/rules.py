"""Rules: missing/contradictions/required fields (V1)."""
from typing import Dict, Any
from .schemas import ClientProfile

MIN_FIELDS = [
    "goal.type",
    "timeline.horizon_months",
    "capacity.monthly_contribution",
    "risk.tolerance_score",
    "knowledge_level",
]


def _get_path(profile: ClientProfile, path: str) -> Any:
    if path.startswith("goal."):
        return profile.goal.get(path.split("goal.", 1)[1])
    if path.startswith("timeline."):
        return profile.timeline.get(path.split("timeline.", 1)[1])
    if path.startswith("capacity."):
        return profile.capacity.get(path.split("capacity.", 1)[1])
    if path.startswith("risk."):
        return profile.risk.get(path.split("risk.", 1)[1])
    if path == "knowledge_level":
        return profile.knowledge_level
    return None


def _confidence(profile: ClientProfile, path: str) -> float:
    return float(profile.confidence.get(path, 0.0))


def evaluate(profile: ClientProfile) -> Dict[str, Any]:
    missing = []
    contradictions = []

    for path in MIN_FIELDS:
        value = _get_path(profile, path)
        confidence = _confidence(profile, path)
        if value is None or confidence < 0.85:
            if path == "risk.tolerance_score":
                horizon = _get_path(profile, "timeline.horizon_months")
                if horizon is not None and float(horizon) <= 12:
                    continue
            missing.append(path)

    target_amount = _get_path(profile, "goal.target_amount")
    if target_amount is not None and float(target_amount) <= 0:
        contradictions.append("goal.target_amount_non_positive")

    monthly = _get_path(profile, "capacity.monthly_contribution")
    if monthly is not None and float(monthly) < 0:
        contradictions.append("capacity.monthly_contribution_negative")

    ready = len(missing) == 0 and len(contradictions) == 0
    return {
        "compliance": {
            "missing_fields": missing,
            "contradictions": contradictions,
            "ready_for_allocation": ready,
            "required_fields": MIN_FIELDS,
        }
    }
