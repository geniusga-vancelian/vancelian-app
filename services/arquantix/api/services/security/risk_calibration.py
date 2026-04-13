"""
Calibration **suggestive** (Phase 5F) — jamais d’application automatique des poids.

Méthode déterministe : comptage par type de feedback et par code de facteur,
règles fixes de suggestion (seuils minima, pas de ML).
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Set

from pydantic import BaseModel, Field

from services.security.risk_feedback import RiskFeedback
from services.security.risk_config import DEFAULT_RISK_WEIGHTS, get_risk_weight


class CalibrationSuggestion(BaseModel):
    factor_code: str
    current_weight: float
    suggested_weight: float
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


def _is_negative_feedback(ft: str) -> bool:
    return ft in ("fraud_confirmed", "fraud_suspected")


def _is_false_positive(ft: str) -> bool:
    return ft == "false_positive"


def _factors_from_feedback(fb: RiskFeedback) -> Set[str]:
    return {str(c).strip() for c in (fb.factor_codes or []) if str(c).strip()}


def compute_calibration_suggestions(
    feedbacks: Sequence[RiskFeedback],
    *,
    min_samples_per_factor: int = 5,
    step: float = 5.0,
    max_step: float = 15.0,
) -> List[CalibrationSuggestion]:
    """
    Produit des **suggestions** uniquement (validation humaine / release requise).

    Règles :
    - Si taux de signaux frauduleux élevé parmi les cas où le facteur est présent → augmenter le poids.
    - Si taux de faux positifs élevé → diminuer le poids (ou le seuil associé — ici poids facteur).
    """
    # Comptages par facteur
    fraud_with: Dict[str, int] = {}
    fp_with: Dict[str, int] = {}
    total_with: Dict[str, int] = {}

    for fb in feedbacks:
        factors = _factors_from_feedback(fb)
        if not factors:
            continue
        ft = fb.feedback_type
        for code in factors:
            total_with[code] = total_with.get(code, 0) + 1
            if _is_negative_feedback(ft):
                fraud_with[code] = fraud_with.get(code, 0) + 1
            if _is_false_positive(ft):
                fp_with[code] = fp_with.get(code, 0) + 1

    suggestions: List[CalibrationSuggestion] = []
    seen: Set[str] = set()

    for code, n in sorted(total_with.items()):
        if n < min_samples_per_factor:
            continue
        f_ct = fraud_with.get(code, 0)
        fp_ct = fp_with.get(code, 0)
        fraud_rate = f_ct / float(n)
        fp_rate = fp_ct / float(n)

        current = get_risk_weight(code, default=DEFAULT_RISK_WEIGHTS.get(code, 0.0))

        # Règle 1 : fraude corrélée
        if f_ct >= 3 and fraud_rate >= 0.4 and fraud_rate > fp_rate:
            delta = min(max_step, step * (1.0 + int(fraud_rate * 5)))
            sug = current + delta if current >= 0 else current - delta
            sug = max(-40.0, min(40.0, sug))
            conf = min(0.95, 0.35 + fraud_rate * 0.5)
            suggestions.append(
                CalibrationSuggestion(
                    factor_code=code,
                    current_weight=round(current, 2),
                    suggested_weight=round(sug, 2),
                    confidence=round(conf, 2),
                    reason=(
                        f"Signal fraude élevé pour ce facteur (fraud={f_ct}/{n}, "
                        f"rate={fraud_rate:.2f}) — suggestion d’augmenter la pondération."
                    ),
                )
            )
            seen.add(code)
            continue

        # Règle 2 : faux positifs
        if fp_ct >= 3 and fp_rate >= 0.4 and fp_rate > fraud_rate and code not in seen:
            delta = min(max_step, step * (1.0 + int(fp_rate * 5)))
            sug = current - delta if current >= 0 else current + delta
            sug = max(-40.0, min(40.0, sug))
            conf = min(0.95, 0.35 + fp_rate * 0.5)
            suggestions.append(
                CalibrationSuggestion(
                    factor_code=code,
                    current_weight=round(current, 2),
                    suggested_weight=round(sug, 2),
                    confidence=round(conf, 2),
                    reason=(
                        f"Faux positifs fréquents (fp={fp_ct}/{n}, rate={fp_rate:.2f}) — "
                        f"suggestion de réduire la pondération ou d’ajuster les seuils métier."
                    ),
                )
            )

    return suggestions
