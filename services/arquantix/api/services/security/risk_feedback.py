"""
Ingestion de feedback terrain sur les décisions de risque (Phase 5F).

Persistance minimale : logs structurés (pas de table obligatoire).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("arquantix.security.risk_feedback")

from services.security.risk_dashboard_store import record_risk_feedback_snapshot

FeedbackType = Literal[
    "fraud_confirmed",
    "fraud_suspected",
    "false_positive",
    "successful_action",
    "manual_override",
]

_FEEDBACK_TYPES = frozenset(
    {
        "fraud_confirmed",
        "fraud_suspected",
        "false_positive",
        "successful_action",
        "manual_override",
    }
)


class RiskFeedback(BaseModel):
    action_key: str
    user_id: str
    risk_score: float
    risk_level: str
    decision: str
    outcome: str
    feedback_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    factor_codes: List[str] = Field(default_factory=list)

    @field_validator("feedback_type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        t = (v or "").strip().lower()
        if t not in _FEEDBACK_TYPES:
            raise ValueError(f"feedback_type must be one of {sorted(_FEEDBACK_TYPES)}")
        return t


def record_risk_feedback(feedback: RiskFeedback) -> None:
    """
    Enregistre un feedback (journal structuré uniquement — pas d’écriture DB implicite).

    Les appelants peuvent compléter ``metadata`` (ex. ticket, source) sans PII inutile.
    """
    payload = {
        "event": "risk_feedback.recorded",
        "action_key": feedback.action_key,
        "user_id_hash": _opaque_user_token(feedback.user_id),
        "risk_score": round(float(feedback.risk_score), 2),
        "risk_level": feedback.risk_level,
        "decision": feedback.decision,
        "outcome": feedback.outcome,
        "feedback_type": feedback.feedback_type,
        "factor_codes": list(feedback.factor_codes),
        "metadata_keys": sorted(feedback.metadata.keys()) if feedback.metadata else [],
    }
    try:
        logger.info("%s %s", payload["event"], json.dumps(payload, default=str, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        logger.info("risk_feedback.recorded (serialization fallback)")
    try:
        record_risk_feedback_snapshot(
            feedback_type=feedback.feedback_type,
            factor_codes=list(feedback.factor_codes),
            action_key=feedback.action_key,
        )
    except Exception:  # noqa: BLE001
        pass


def _opaque_user_token(user_id: str) -> str:
    """Hachage court déterministe pour logs (non réversible pour l’observateur du log)."""
    import hashlib

    raw = str(user_id or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
