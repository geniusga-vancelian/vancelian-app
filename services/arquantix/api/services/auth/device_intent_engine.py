"""PR F.6 — Intent Engine : séquences d’actions suspectes (complément au score comportemental)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import AuthUserIntentEvent
from services.auth.device_risk_engine_pr_f import RiskEvaluationResult
from services.auth.device_risk_engine_pr_f2 import step_up_zone_score
from services.auth.device_risk_engine_pr_f3 import infer_risk_action_type
from services.security.security_env import is_device_intent_engine_enabled

logger = logging.getLogger("arquantix.auth.device_intent_engine")

# Fenêtres (secondes) — patterns initiaux
WINDOW_SEQUENCE_SEC = 600
WINDOW_STEP_UP_SPAM_SEC = 600
STEP_UP_SPAM_THRESHOLD = 3


def log_intent_event(
    db: Session,
    *,
    user_id: int,
    device_id: str,
    action_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    risk_decision: Optional[str] = None,
) -> None:
    """Persiste une ligne d’historique intent (appelé après évaluation PR F)."""
    meta: Dict[str, Any] = dict(metadata or {})
    if risk_decision is not None:
        meta["risk_decision"] = risk_decision
    row = AuthUserIntentEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        device_id=(device_id or "")[:128],
        action_type=(action_type or "unknown")[:64],
        metadata_payload=meta,
    )
    db.add(row)
    db.flush()


def get_recent_user_actions(db: Session, *, user_id: int, window_sec: int) -> List[AuthUserIntentEvent]:
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
    return (
        db.query(AuthUserIntentEvent)
        .filter(
            AuthUserIntentEvent.user_id == user_id,
            AuthUserIntentEvent.created_at >= since,
        )
        .order_by(AuthUserIntentEvent.created_at.asc())
        .all()
    )


def count_prior_step_up_decisions(db: Session, *, user_id: int, window_sec: int) -> int:
    """Nombre d’événements issus de requêtes ayant abouti à ``step_up`` (méta), hors requête courante."""
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
    return (
        db.query(AuthUserIntentEvent)
        .filter(
            AuthUserIntentEvent.user_id == user_id,
            AuthUserIntentEvent.created_at >= since,
        )
        .filter(text("auth_user_intent_events.metadata->>'risk_decision' = 'step_up'"))
        .count()
    )


def _tail_sequence_matches(chain: List[str], pattern: List[str]) -> bool:
    if len(chain) < len(pattern):
        return False
    return chain[-len(pattern) :] == pattern


def match_intent_patterns(
    *,
    prior_action_types: List[str],
    current_action: str,
    prior_step_up_count: int,
) -> Optional[Tuple[str, List[str]]]:
    """
    Retourne (``block`` | ``step_up``, raisons) ou None.

    Ordre : spam step-up (bloque) puis séquences métier.
    """
    if prior_step_up_count >= STEP_UP_SPAM_THRESHOLD:
        return "block", ["intent_repeated_step_up_window"]

    chain = prior_action_types + [current_action]

    if _tail_sequence_matches(chain, ["beneficiary_add", "withdrawal"]):
        return "block", ["intent_beneficiary_then_withdrawal"]
    if _tail_sequence_matches(chain, ["login", "withdrawal"]):
        return "step_up", ["intent_login_then_withdrawal"]
    return None


def evaluate_intent_engine(
    db: Session,
    *,
    request: Request,
    user_id: int,
    device_id: str,
    result: RiskEvaluationResult,
) -> RiskEvaluationResult:
    """
    Surcharge éventuelle de la décision PR F selon l’historique d’intentions.

    - ``block`` intent : prioritaire sur allow / step_up.
    - ``step_up`` intent : renforce allow → step_up ; laisse block inchangé.
    """
    if not is_device_intent_engine_enabled():
        return result

    inferred = infer_risk_action_type(request)
    recent = get_recent_user_actions(db, user_id=user_id, window_sec=WINDOW_SEQUENCE_SEC)
    prior_types = [str(r.action_type or "") for r in recent]
    prior_step_ups = count_prior_step_up_decisions(db, user_id=user_id, window_sec=WINDOW_STEP_UP_SPAM_SEC)

    matched = match_intent_patterns(
        prior_action_types=prior_types,
        current_action=inferred,
        prior_step_up_count=prior_step_ups,
    )
    if matched is None:
        return result

    intent_decision, intent_reasons = matched
    reasons = list(result.risk_reasons)
    reasons.extend(intent_reasons)

    if intent_decision == "block":
        logger.info(
            "device_intent_engine_block",
            extra={
                "event": "device_intent_engine_block",
                "user_id": user_id,
                "reasons": intent_reasons,
            },
        )
        return RiskEvaluationResult(
            score=min(100, max(result.score, 100)),
            decision="block",
            context=result.context,
            risk_reasons=reasons,
            dry_run_result=result.dry_run_result,
            triggered_rule_name="intent_engine",
            triggered_rule_conditions={"pattern": intent_reasons[0] if intent_reasons else None},
        )

    # step_up
    if result.decision == "block":
        return result
    logger.info(
        "device_intent_engine_step_up",
        extra={
            "event": "device_intent_engine_step_up",
            "user_id": user_id,
            "reasons": intent_reasons,
        },
    )
    return RiskEvaluationResult(
        score=step_up_zone_score(),
        decision="step_up",
        context=result.context,
        risk_reasons=reasons,
        dry_run_result=result.dry_run_result,
        triggered_rule_name="intent_engine",
        triggered_rule_conditions={"pattern": intent_reasons[0] if intent_reasons else None},
    )
