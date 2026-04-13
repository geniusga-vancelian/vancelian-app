"""FastAPI Depends — auth continue sur actions sensibles (sans stack parallèle)."""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY, get_current_user
from database import AdminUser, AuthSession, get_db
from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event
from services.security.continuous_auth_engine import (
    evaluate_request_security_context,
    is_continuous_auth_enabled,
    next_step_hint,
)
from services.security.risk_engine import extract_behavioral_context
from services.security.security_env import is_behavioral_risk_enabled
from services.security.continuous_auth_ux import build_continuous_auth_ux_fields
from services.security.session_intelligence_service import (
    get_intelligence_for_session,
    is_session_intelligence_enabled,
)


def _parse_transfer_amount_eur(request: Request) -> Optional[float]:
    h = request.headers.get("x-transfer-amount-eur") or request.headers.get("X-Transfer-Amount-Eur")
    if not h:
        return None
    try:
        return float(str(h).strip().replace(",", "."))
    except ValueError:
        return None


def _parse_same_owner(request: Request) -> Optional[bool]:
    h = request.headers.get("x-transfer-same-owner") or request.headers.get("X-Transfer-Same-Owner")
    if not h:
        return None
    s = str(h).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return None


def _parse_recent_similar_actions(request: Request) -> Optional[int]:
    h = request.headers.get("x-recent-similar-actions") or request.headers.get("X-Recent-Similar-Actions")
    if not h or str(h).strip() == "":
        return None
    try:
        return int(str(h).strip())
    except ValueError:
        return None


def _detail_payload(
    *,
    code: str,
    message: str,
    action_key: str,
    dec: Any,
) -> Dict[str, Any]:
    policy = getattr(dec, "policy", None)
    pdict: Dict[str, Any] = {}
    if policy is not None:
        pdict = {
            "required_auth_level": getattr(policy.required_auth_level, "value", None),
            "requires_step_up": policy.requires_step_up,
            "requires_recent_auth_seconds": policy.requires_recent_auth_seconds,
            "requires_biometric": policy.requires_biometric,
            "allowed_if_device_trusted_only": policy.allowed_if_device_trusted_only,
        }
    out: Dict[str, Any] = {
        "code": code,
        "message": message,
        "action_key": action_key,
        "reason_codes": list(dec.reason_codes),
        "next_step": next_step_hint(dec),
        "policy": pdict,
    }
    rs = getattr(dec, "risk_score", None)
    if rs is not None:
        out["risk_score"] = rs
        out["risk_level"] = getattr(dec, "risk_level", None)
        rf = getattr(dec, "risk_factors", None) or []
        out["risk_factors"] = list(rf)
        ro = getattr(dec, "recommended_outcome", None)
        if ro:
            out["recommended_outcome"] = ro
    fk = getattr(dec, "final_action_key", None)
    if fk and fk != action_key:
        out["final_action_key"] = fk
    out.update(
        build_continuous_auth_ux_fields(
            reason_codes=list(dec.reason_codes),
            action_key=action_key,
            risk_level=getattr(dec, "risk_level", None),
        )
    )
    return out


def require_continuous_auth_for_action(action_key: str) -> Callable:
    """
    Bloque uniquement si CONTINUOUS_AUTH + SESSION_INTELLIGENCE actifs et décision ``allow=False``.
    Jeton sans ``sid`` : pas d’intelligence → laisser passer (rétrocompat).

    Réponses structurées (``detail``) : ``session.reauth_required`` (401),
    ``session.step_up_required`` (403), ``session.continuous_auth_denied`` (403).
    """

    def _dep(
        request: Request,
        db: Session = Depends(get_db),
        current_user: AdminUser = Depends(get_current_user),
    ) -> AdminUser:
        if not is_continuous_auth_enabled() or not is_session_intelligence_enabled():
            return current_user
        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            return current_user
        token = auth[7:].strip()
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return current_user
        sid = payload.get("sid")
        if not sid:
            return current_user
        try:
            su = uuid.UUID(str(sid))
        except (ValueError, TypeError):
            return current_user
        session = (
            db.query(AuthSession)
            .filter(
                AuthSession.id == su,
                AuthSession.user_id == current_user.id,
                AuthSession.revoked_at.is_(None),
            )
            .first()
        )
        if session is None:
            return current_user
        intel = get_intelligence_for_session(db, su)

        dev = (request.headers.get("x-device-id") or "")[:128]
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        if ua and len(ua) > 512:
            ua = ua[:512]

        def _audit(event_type: str, extra: dict) -> None:
            if not is_security_events_enabled():
                return
            persist_auth_security_event(
                user_id=current_user.id,
                device_id=dev,
                event_type=event_type,
                ip_address=ip,
                user_agent=ua,
                metadata={
                    "session_id": str(su),
                    "user_id": current_user.id,
                    "risk_score": getattr(intel, "last_risk_score", None) if intel else None,
                    "device_trust": getattr(intel, "device_trust_level", None) if intel else None,
                    **extra,
                },
                db=db,
            )

        _audit(
            "sensitive_action.requested",
            {"action_key": action_key, "reason_codes": ["evaluation_started"]},
        )

        transfer_amount: Optional[float] = None
        if action_key == "wallet_transfer":
            transfer_amount = _parse_transfer_amount_eur(request)

        same_owner = _parse_same_owner(request) if action_key == "wallet_transfer" else None
        similar_recent = _parse_recent_similar_actions(request)

        behavioral_ctx = None
        if is_behavioral_risk_enabled():
            behavioral_ctx = extract_behavioral_context(request, current_user, intel, session)

        dec = evaluate_request_security_context(
            session,
            request,
            intel,
            sensitive_action=action_key,
            transfer_amount_eur=transfer_amount,
            same_owner=same_owner,
            similar_actions_recent_count=similar_recent,
            current_user=current_user,
            behavioral_context=behavioral_ctx,
        )
        if dec.allow:
            return current_user

        meta = {
            "session_id": str(su),
            "user_id": current_user.id,
            "risk_score": getattr(intel, "last_risk_score", None) if intel else None,
            "device_trust": getattr(intel, "device_trust_level", None) if intel else None,
            "reason_codes": dec.reason_codes,
            "action_key": action_key,
        }

        if dec.require_reauth:
            _audit("auth.session.reauth.triggered", {"action": action_key})
            _audit("sensitive_action.reauth_required", meta)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_detail_payload(
                    code="session.reauth_required",
                    message="Une nouvelle authentification complète est requise.",
                    action_key=action_key,
                    dec=dec,
                ),
            )
        if dec.require_step_up:
            _audit("auth.session.step_up.triggered", {"action": action_key})
            _audit("sensitive_action.step_up_required", meta)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_detail_payload(
                    code="session.step_up_required",
                    message="Vérification supplémentaire requise (OTP / passkey).",
                    action_key=action_key,
                    dec=dec,
                ),
            )
        _audit("sensitive_action.blocked", meta)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                **_detail_payload(
                    code="session.continuous_auth_denied",
                    message="Action refusée par la politique d’authentification continue.",
                    action_key=action_key,
                    dec=dec,
                ),
            },
        )

    return _dep
