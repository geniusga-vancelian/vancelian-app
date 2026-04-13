"""
Session Intelligence — état par session, mis à jour sur refresh / requêtes / actions sensibles.
Réutilise fraude ML, réputation device, scores globaux existants. Aucune stack parallèle.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastapi import Request
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from database import AuthSession

from services.security.security_env import (
    is_session_intelligence_enabled,
    is_session_reauth_enabled,
    is_session_step_up_enabled,
)

logger = logging.getLogger("arquantix.security.session_intelligence")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _country_from_request(request: Request) -> Optional[str]:
    for h in ("cf-ipcountry", "CF-IPCountry", "x-geo-country", "X-Geo-Country"):
        v = request.headers.get(h)
        if v and str(v).strip():
            return str(v).strip()[:8]
    return None


def _client_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None


def _persist_intel_event(
    *,
    event_type: str,
    user_id: int,
    device_id: str,
    request: Optional[Request],
    metadata: Dict[str, Any],
    db: Session,
) -> None:
    try:
        from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event

        if not is_security_events_enabled():
            return
        ip = _client_ip(request) if request else None
        ua = request.headers.get("user-agent") if request else None
        if ua and len(ua) > 512:
            ua = ua[:512]
        persist_auth_security_event(
            user_id=user_id,
            device_id=device_id or "",
            event_type=event_type,
            ip_address=ip,
            user_agent=ua,
            metadata=metadata,
            db=db,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("session_intel event failed: %s", exc)


def _reason_list(intel_row: Any) -> List[str]:
    raw = getattr(intel_row, "reason_codes_json", None)
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _set_reasons(intel_row: Any, codes: List[str]) -> None:
    intel_row.reason_codes_json = list(dict.fromkeys(codes))[:32]


def get_intelligence_for_session(db: Session, session_id: uuid.UUID) -> Optional[Any]:
    from database import AuthSessionIntelligence

    return (
        db.query(AuthSessionIntelligence)
        .filter(AuthSessionIntelligence.session_id == session_id)
        .first()
    )


def initialize_session_intelligence(
    db: Session,
    session: "AuthSession",
    orchestrator_decision: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Crée la ligne intelligence au premier jeton (login / issue session)."""
    if not is_session_intelligence_enabled():
        return None
    from database import AuthSessionIntelligence

    existing = get_intelligence_for_session(db, session.id)
    if existing:
        return existing

    orch = orchestrator_decision or {}
    session_trust = str(orch.get("session_trust_target") or "UNKNOWN")[:32]
    auth_strength = str(getattr(session, "auth_strength", None) or "password")[:64]
    device_trust = str(getattr(session, "device_trust_level", None) or "UNKNOWN")[:32]
    step_up = bool(getattr(session, "step_up_otp_required", False)) or bool(orch.get("step_up_required"))

    row = AuthSessionIntelligence(
        id=uuid.uuid4(),
        session_id=session.id,
        user_id=session.user_id,
        auth_strength=auth_strength,
        session_trust_level=session_trust,
        device_trust_level=device_trust,
        last_risk_score=0,
        last_fraud_score=None,
        last_activity_at=_utcnow(),
        last_sensitive_action_at=None,
        last_ip=getattr(session, "ip_address", None),
        last_country=None,
        relock_required=False,
        step_up_required=step_up,
        last_step_up_at=None,
        reason_codes_json=["initialized"],
    )
    db.add(row)
    db.flush()
    _persist_intel_event(
        event_type="auth.session.intelligence.updated",
        user_id=session.user_id,
        device_id=getattr(session, "device_id", "") or "",
        request=None,
        metadata={
            "session_id": str(session.id),
            "risk_score": 0,
            "device_trust": device_trust,
            "reason_codes": ["initialized"],
        },
        db=db,
    )
    return row


def evaluate_session_risk(
    db: Session,
    *,
    user_id: int,
    intel: Any,
    fraud_hybrid: Optional[float],
) -> int:
    """Score 0–100 agrégé (heuristique explicable, sans réinjecter l’ancien score en boucle)."""
    score = 0
    try:
        from database import AuthGlobalRiskScore

        gr = db.query(AuthGlobalRiskScore).filter(AuthGlobalRiskScore.user_id == user_id).first()
        if gr and getattr(gr, "score", None) is not None:
            score = max(score, min(100, int(gr.score)))
    except Exception:  # noqa: BLE001
        pass

    if fraud_hybrid is not None:
        score = max(score, min(100, int(float(fraud_hybrid) * 100)))

    reasons = _reason_list(intel)
    if "ip_changed" in reasons:
        score = min(100, score + 15)
    if "country_changed" in reasons:
        score = min(100, score + 35)
    if "fingerprint_changed" in reasons:
        score = min(100, score + 25)

    low_trust = str(getattr(intel, "device_trust_level", "") or "").upper()
    if low_trust in ("LOW", "UNKNOWN", "UNTRUSTED"):
        score = min(100, score + 10)

    return min(100, max(0, score))


def compute_session_trust(intel: Any) -> str:
    """Niveau de confiance de session dérivé (HIGH / MEDIUM / LOW)."""
    risk = int(getattr(intel, "last_risk_score", 0) or 0)
    dt = str(getattr(intel, "device_trust_level", "") or "").upper()
    st = str(getattr(intel, "session_trust_level", "") or "").upper()
    if risk >= 70 or getattr(intel, "step_up_required", False):
        return "LOW"
    if risk >= 40 or dt in ("LOW", "UNKNOWN") or st in ("LOW", "UNKNOWN"):
        return "MEDIUM"
    if dt == "HIGH" and risk < 25:
        return "HIGH"
    return "MEDIUM"


def should_require_step_up(intel: Any, action_tier: str) -> bool:
    if not is_session_step_up_enabled():
        return False
    if getattr(intel, "step_up_required", False):
        return True
    risk = int(getattr(intel, "last_risk_score", 0) or 0)
    if action_tier == "high" and risk >= 35:
        return True
    if action_tier == "medium" and risk >= 55:
        return True
    return False


def should_force_reauth(intel: Any, action_tier: str) -> bool:
    if not is_session_reauth_enabled():
        return False
    reasons = _reason_list(intel)
    if "country_changed" in reasons:
        return action_tier in ("high", "medium")
    if int(getattr(intel, "last_risk_score", 0) or 0) >= 85:
        return True
    return False


def should_relock_local(intel: Any) -> bool:
    """Signal client (JWT / header) — relock app plus agressif."""
    return bool(getattr(intel, "relock_required", False)) or int(
        getattr(intel, "last_risk_score", 0) or 0
    ) >= 60


def update_session_intelligence_on_request(
    db: Session,
    session: "AuthSession",
    request: Request,
    *,
    fingerprint_changed: bool = False,
    ip_changed: bool = False,
) -> Optional[Any]:
    """Refresh ou requête authentifiée : activité, IP/pays, risque."""
    if not is_session_intelligence_enabled():
        return None
    from database import AuthSessionIntelligence

    intel = get_intelligence_for_session(db, session.id)
    if intel is None:
        intel = initialize_session_intelligence(db, session, None)
    if intel is None:
        return None

    now = _utcnow()
    ip = _client_ip(request)
    country = _country_from_request(request)
    reasons = _reason_list(intel)

    prev_ip = intel.last_ip
    prev_country = intel.last_country

    intel.last_activity_at = now
    if ip:
        intel.last_ip = ip
    if country:
        intel.last_country = country

    if ip_changed or (prev_ip and ip and prev_ip != ip):
        if "ip_changed" not in reasons:
            reasons.append("ip_changed")
    if prev_country and country and prev_country != country:
        if "country_changed" not in reasons:
            reasons.append("country_changed")
    if fingerprint_changed and "fingerprint_changed" not in reasons:
        reasons.append("fingerprint_changed")

    fraud_score: Optional[float] = None
    try:
        from services.auth.refresh_session import normalize_device_id
        from services.auth.device_fingerprint import is_device_fingerprint_enabled, parse_device_fingerprint_header
        from services.security.device_reputation.device_reputation_service import resolve_device_hash_from_request
        from services.security.ml.login_fraud_evaluator import (
            evaluate_refresh_fraud_risk,
            is_login_fraud_evaluation_enabled,
        )

        if is_login_fraud_evaluation_enabled():
            raw = request.headers.get("x-device-fingerprint")
            _, fp_hash = parse_device_fingerprint_header(raw)
            dev = normalize_device_id(request.headers.get("x-device-id"))
            dh = resolve_device_hash_from_request(request, dev, fp_hash)
            if dh:
                ev = evaluate_refresh_fraud_risk(
                    db,
                    session.user_id,
                    device_hash=dh,
                    ip=ip,
                    session_id=session.id,
                )
                fraud_score = ev.get("hybrid_score")
                if fraud_score is not None and float(fraud_score) >= 0.75:
                    reasons.append("fraud_high")
    except Exception as exc:  # noqa: BLE001
        logger.debug("fraud refresh in intel skipped: %s", exc)

    intel.last_fraud_score = fraud_score
    _set_reasons(intel, reasons)

    old_risk = int(getattr(intel, "last_risk_score", 0) or 0)
    prev_step_up = bool(getattr(intel, "step_up_required", False))

    new_risk = evaluate_session_risk(
        db,
        user_id=session.user_id,
        intel=intel,
        fraud_hybrid=fraud_score,
    )
    intel.last_risk_score = new_risk
    intel.session_trust_level = compute_session_trust(intel)

    if "country_changed" in reasons:
        intel.relock_required = True
        intel.step_up_required = True
    elif "fraud_high" in reasons or intel.last_risk_score >= 70:
        intel.relock_required = True
        intel.step_up_required = True

    meta_base = {
        "session_id": str(session.id),
        "risk_score": intel.last_risk_score,
        "device_trust": intel.device_trust_level,
        "reason_codes": _reason_list(intel),
    }
    _persist_intel_event(
        event_type="auth.session.intelligence.updated",
        user_id=session.user_id,
        device_id=session.device_id,
        request=request,
        metadata=meta_base,
        db=db,
    )
    if abs(new_risk - old_risk) >= 5:
        _persist_intel_event(
            event_type="auth.session.risk_changed",
            user_id=session.user_id,
            device_id=session.device_id,
            request=request,
            metadata={**meta_base, "previous_risk_score": old_risk},
            db=db,
        )
    if intel.step_up_required and not prev_step_up:
        _persist_intel_event(
            event_type="auth.session.step_up.triggered",
            user_id=session.user_id,
            device_id=session.device_id,
            request=request,
            metadata=meta_base,
            db=db,
        )
    return intel


def touch_last_activity_from_token(db: Session, *, session_uuid: uuid.UUID, request: Request) -> None:
    """Mise à jour légère (middleware) : horodatage d’activité + IP, sans réévaluation fraude complète."""
    if not is_session_intelligence_enabled():
        return
    from database import AuthSession

    session = (
        db.query(AuthSession)
        .filter(AuthSession.id == session_uuid, AuthSession.revoked_at.is_(None))
        .first()
    )
    if session is None:
        return
    intel = get_intelligence_for_session(db, session_uuid)
    if intel is None:
        intel = initialize_session_intelligence(db, session, None)
    if intel is None:
        return
    intel.last_activity_at = _utcnow()
    ip = _client_ip(request)
    if ip:
        intel.last_ip = ip
    c = _country_from_request(request)
    if c:
        intel.last_country = c
    db.add(intel)
    db.commit()


def mark_sensitive_action(db: Session, session: "AuthSession", request: Optional[Request] = None) -> None:
    if not is_session_intelligence_enabled():
        return
    intel = get_intelligence_for_session(db, session.id)
    if intel is None:
        intel = initialize_session_intelligence(db, session, None)
    if intel is None:
        return
    intel.last_sensitive_action_at = _utcnow()
    if request is not None:
        update_session_intelligence_on_request(db, session, request)


def sync_session_row_from_intelligence(session: "AuthSession", intel: Any) -> None:
    """Aligne les flags session SQL avec l’intelligence (step-up OTP)."""
    if intel is None:
        return
    if getattr(intel, "step_up_required", False):
        session.step_up_otp_required = True
