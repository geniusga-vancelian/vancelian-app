"""
Contexte de sécurité par requête — agrège sessions, risque, device, JWT.
Réutilise auth_sessions, auth_global_risk_score, réputation device, inférence fraude (optionnelle).
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import AdminUser, AuthGlobalRiskScore, AuthSession


def _truthy(name: str, default: str = "false") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def is_zero_trust_enforced() -> bool:
    return _truthy("ZERO_TRUST_ENFORCE_DEFAULT_ACCESS", "false")


@dataclass
class RequestSecurityContext:
    user_id: int
    session_id: Optional[str]
    device_id: str
    device_hash: Optional[str]
    device_trust_level: str
    device_reputation_blocked: bool
    global_risk_score: int
    fraud_score: Optional[float]
    ip_address: Optional[str]
    geo_country: Optional[str]
    step_up_required: bool
    account_locked: bool
    roles: List[str]
    auth_strength: str
    attestation_status: str

    def snapshot_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _client_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None


def _resolve_active_session(
    db: Session,
    *,
    user_id: int,
    device_id: str,
) -> Optional[AuthSession]:
    now = datetime.now(timezone.utc)
    return (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user_id,
            AuthSession.device_id == device_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_used_at.desc())
        .first()
    )


def _attestation_status(session: Optional[AuthSession]) -> str:
    if session is None:
        return "none"
    if session.attestation_verified_at is not None:
        return "verified"
    if session.attestation_type:
        return "partial"
    return "none"


def build_request_security_context(
    *,
    db: Session,
    request: Request,
    user: AdminUser,
    access_token: str,
    device_header: Optional[str] = None,
    jwt_payload: Optional[Dict[str, Any]] = None,
) -> RequestSecurityContext:
    """
    Construit le contexte unique pour une requête authentifiée Bearer.

    - device_id : en-tête X-Device-ID ou valeur normalisée legacy.
    - session : meilleure session active (user + device).
    - device_hash : si DEVICE_REPUTATION_ENABLED.
    - fraud_score : inférence ML si FRAUD_ML_INFERENCE_ENABLED (best-effort).
    """
    from services.auth.refresh_session import normalize_device_id
    from services.auth.device_fingerprint import is_device_fingerprint_enabled, parse_device_fingerprint_header

    from auth import ALGORITHM, SECRET_KEY

    payload: Dict[str, Any] = {}
    if jwt_payload is not None:
        payload = jwt_payload
    else:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            payload = {}

    device_id = normalize_device_id(device_header)
    fp_meta, fp_hash = parse_device_fingerprint_header(request.headers.get("x-device-fingerprint"))
    _ = fp_meta

    device_hash: Optional[str] = None
    device_blocked = False
    try:
        from services.security.device_reputation.device_reputation_service import (
            is_device_blacklisted,
            is_device_reputation_enabled,
            resolve_device_hash_from_request,
        )

        if is_device_reputation_enabled():
            device_hash = resolve_device_hash_from_request(request, device_id, fp_hash if is_device_fingerprint_enabled() else None)
            device_blocked = is_device_blacklisted(db, device_hash)
    except Exception:
        device_hash = None
        device_blocked = False

    session = _resolve_active_session(db, user_id=user.id, device_id=device_id)
    session_id_str = str(session.id) if session else None

    grs = db.query(AuthGlobalRiskScore).filter(AuthGlobalRiskScore.user_id == user.id).first()
    global_risk = int(grs.score) if grs is not None else 0

    fraud_score: Optional[float] = None
    try:
        from services.security.fraud_ml_inference_service import is_fraud_ml_inference_enabled, predict_user_risk_ml

        if is_fraud_ml_inference_enabled():
            ml_out = predict_user_risk_ml(db, user.id)
            if isinstance(ml_out, dict) and ml_out.get("ok"):
                fraud_score = float(ml_out.get("ml_score") or 0.0)
    except Exception:
        fraud_score = None

    now = datetime.now(timezone.utc)
    locked_until = getattr(user, "security_account_locked_until", None)
    account_locked = locked_until is not None and locked_until > now

    zt_role = getattr(user, "zero_trust_role", None) or "admin"
    roles = [str(zt_role)]

    auth_strength = str(payload.get("auth_str") or (session.auth_strength if session else None) or "password")
    device_trust = str(
        payload.get("dtrust")
        or (session.device_trust_level if session else None)
        or "UNKNOWN",
    )

    step_up = bool(session.step_up_otp_required) if session else False

    geo = request.headers.get("x-geo-country") or request.headers.get("X-Geo-Country")
    if geo:
        geo = str(geo).strip()[:8] or None

    return RequestSecurityContext(
        user_id=user.id,
        session_id=session_id_str,
        device_id=device_id,
        device_hash=device_hash,
        device_trust_level=device_trust,
        device_reputation_blocked=device_blocked,
        global_risk_score=global_risk,
        fraud_score=fraud_score,
        ip_address=_client_ip(request),
        geo_country=geo,
        step_up_required=step_up,
        account_locked=account_locked,
        roles=roles,
        auth_strength=auth_strength,
        attestation_status=_attestation_status(session),
    )
