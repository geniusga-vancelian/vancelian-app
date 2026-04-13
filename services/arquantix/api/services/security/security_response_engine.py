"""
Moteur de réponse automatique Tier-1 (score global → OTP, révocation, verrouillage).

Seuils :
  >= 70 : step-up OTP sur les sessions actives
  >= 90 : révocation sessions, blocage refresh, compte flaggé
  >= 95 : verrouillage temporaire du compte
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import AdminUser, AuthDeviceReputation, AuthDeviceUsageEdge, AuthGlobalRiskScore, AuthSession
from services.auth.refresh_session import _spend_jti_safe
from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event
from services.auth.security_signal_service import SecuritySignalService
from services.security.security_correlation_engine import assess_user_risk
from services.security.security_env import (
    fraud_ml_enforce_min_heuristic,
    global_risk_ml_weight,
    is_device_reputation_risk_engine_integration_enabled,
    is_security_response_engine_enabled,
    security_account_lock_hours,
)

logger = logging.getLogger("arquantix.security.response_engine")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _lock_hours() -> int:
    return security_account_lock_hours()


def _fraud_boost_for_user(db: Session, user_id: int) -> int:
    flags = SecuritySignalService.detect_anomalies(db)
    pts = 0
    details = flags.get("details") or {}
    if flags.get("suspicious_user") and user_id in (details.get("users_ip_and_fingerprint_change") or []):
        pts += 18
    if flags.get("suspicious_device"):
        pts += 12
    if flags.get("suspicious_ip"):
        pts += 10
    return min(35, pts)


def _device_trust_boost(db: Session, user_id: int) -> int:
    now = _utcnow()
    n = (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
            AuthSession.device_trust_level.in_(("SUSPICIOUS", "BLOCKED")),
        )
        .count()
    )
    return min(30, n * 12)


def _device_reputation_user_boost(db: Session, user_id: int) -> int:
    """Contribution progressive au score utilisateur depuis les devices récemment vus."""
    if not is_device_reputation_risk_engine_integration_enabled():
        return 0
    try:
        from services.security.device_reputation.device_reputation_service import is_device_reputation_enabled

        if not is_device_reputation_enabled():
            return 0
    except Exception:  # noqa: BLE001
        return 0
    since = _utcnow() - timedelta(days=30)
    hashes = (
        db.execute(
            select(AuthDeviceUsageEdge.device_hash)
            .where(
                AuthDeviceUsageEdge.user_id == user_id,
                AuthDeviceUsageEdge.created_at >= since,
            )
            .distinct()
            .limit(80)
        )
        .scalars()
        .all()
    )
    best = 0
    for h in hashes:
        r = db.get(AuthDeviceReputation, h)
        if r is not None:
            best = max(best, int(r.global_risk_score or 0))
    return min(24, best // 5)


def _level_from_int(score: int) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def _heuristic_risk_score(db: Session, user_id: int) -> int:
    """Score 0–100 SIEM + signaux fraude + confiance appareil + réputation device (sans ML)."""
    assessment = assess_user_risk(db, user_id)
    raw = (
        assessment.risk_score
        + _fraud_boost_for_user(db, user_id)
        + _device_trust_boost(db, user_id)
        + _device_reputation_user_boost(db, user_id)
    )
    return max(0, min(100, raw))


def _ml_weight() -> float:
    return global_risk_ml_weight()


def _ml_enforce_gate() -> int:
    """Tant que l’heuristique est sous ce seuil, les actions automatiques n’intègrent pas le blend ML."""
    return fraud_ml_enforce_min_heuristic()


def compute_global_risk_score_with_detail(db: Session, user_id: int) -> tuple[int, str, Dict[str, Any]]:
    """
    Score final pour persistance / enforcement, avec détail (heuristique, ML, hybride).

    Hybride : (1 - ML_WEIGHT) * heuristic + ML_WEIGHT * ml_score.
    Sécurité : si heuristic < FRAUD_ML_ENFORCE_MIN_HEURISTIC, le score appliqué reste l’heuristique
    (le ML ne peut pas à lui seul déclencher blocage / step-up).
    """
    h = _heuristic_risk_score(db, user_id)
    from services.security.fraud_ml_inference_service import predict_user_risk_ml

    ml = predict_user_risk_ml(db, user_id)
    w = _ml_weight()
    if ml.get("ok"):
        hybrid = int(round((1.0 - w) * h + w * float(ml.get("ml_score") or 0.0)))
    else:
        hybrid = h
    hybrid = max(0, min(100, hybrid))
    gate = _ml_enforce_gate()
    enforcement = int(hybrid if h >= gate else h)
    level = _level_from_int(enforcement)
    detail: Dict[str, Any] = {
        "heuristic_score": h,
        "hybrid_score": hybrid,
        "ml_score": ml.get("ml_score"),
        "ml_confidence": ml.get("confidence"),
        "ml_ok": bool(ml.get("ok")),
        "model_version": ml.get("model_version"),
        "ml_weight": w,
        "enforcement_score": enforcement,
        "ml_enforce_gate": gate,
    }
    return enforcement, level, detail


def compute_global_risk_score(db: Session, user_id: int) -> tuple[int, str]:
    s, lvl, _ = compute_global_risk_score_with_detail(db, user_id)
    return s, lvl


def _upsert_global_risk_row(db: Session, user_id: int, score: int, level: str) -> None:
    row = db.query(AuthGlobalRiskScore).filter(AuthGlobalRiskScore.user_id == user_id).first()
    now = _utcnow()
    if row:
        row.score = score
        row.level = level
        row.updated_at = now
    else:
        db.add(AuthGlobalRiskScore(user_id=user_id, score=score, level=level, updated_at=now))


def _emit_action(
    db: Optional[Session],
    *,
    user_id: int,
    device_id: str,
    event_type: str,
    score: int,
    action_taken: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not is_security_events_enabled():
        return
    meta: Dict[str, Any] = {
        "global_risk_score": score,
        "action_taken": action_taken,
        "skip_security_response_engine": True,
    }
    if extra:
        meta.update(extra)
    try:
        meta_json = json.loads(json.dumps(meta, default=str))
    except Exception:  # noqa: BLE001
        meta_json = meta
    persist_auth_security_event(
        user_id=user_id,
        device_id=(device_id or "server")[:128],
        event_type=event_type,
        ip_address=None,
        user_agent=None,
        metadata=meta_json,
        db=db,
    )


def _revoke_all_sessions(db: Session, user_id: int) -> int:
    now = _utcnow()
    q = db.query(AuthSession).filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    n = 0
    for s in q.all():
        s.revoked_at = now
        s.revoke_reason = "security_risk_score"
        _spend_jti_safe(db, s.refresh_jti)
        n += 1
    return n


def _set_step_up_all_sessions(db: Session, user_id: int) -> None:
    now = _utcnow()
    for s in (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None), AuthSession.expires_at > now)
        .all()
    ):
        s.step_up_otp_required = True


def recompute_user_risk_and_enforce(db: Optional[Session], user_id: int) -> Dict[str, Any]:
    """
    Recalcule le score, persiste ``auth_global_risk_score``, applique les seuils.
    À appeler depuis le pipeline SIEM (même transaction que l’événement déclencheur si possible).
    """
    out: Dict[str, Any] = {"user_id": user_id, "actions": []}
    if not user_id or not is_security_response_engine_enabled():
        return out
    if db is None:
        return out

    user = db.get(AdminUser, user_id)
    if user is None:
        return out

    score, level = compute_global_risk_score(db, user_id)
    _upsert_global_risk_row(db, user_id, score, level)

    if score >= 95:
        user.security_account_locked_until = _utcnow() + timedelta(hours=_lock_hours())
        user.security_refresh_blocked = True
        user.security_flagged = True
        n = _revoke_all_sessions(db, user_id)
        _emit_action(
            db,
            user_id=user_id,
            device_id="server",
            event_type="auth.security.action.blocked",
            score=score,
            action_taken="temporary_account_lock",
            extra={"revoked_sessions": n, "level": level},
        )
        out["actions"].append("temporary_account_lock")
        logger.warning("security.response lock user=%s score=%s", user_id, score)

    elif score >= 90:
        user.security_refresh_blocked = True
        user.security_flagged = True
        n = _revoke_all_sessions(db, user_id)
        _emit_action(
            db,
            user_id=user_id,
            device_id="server",
            event_type="auth.security.action.revoked",
            score=score,
            action_taken="revoke_sessions_block_refresh_flag",
            extra={"revoked_sessions": n, "level": level},
        )
        out["actions"].append("revoke_sessions_block_refresh_flag")
        logger.warning("security.response revoke user=%s score=%s", user_id, score)

    elif score >= 70:
        _set_step_up_all_sessions(db, user_id)
        _emit_action(
            db,
            user_id=user_id,
            device_id="server",
            event_type="auth.security.action.step_up",
            score=score,
            action_taken="require_otp_step_up",
            extra={"level": level},
        )
        out["actions"].append("require_otp_step_up")
        logger.info("security.response step_up user=%s score=%s", user_id, score)

    db.flush()
    return out
