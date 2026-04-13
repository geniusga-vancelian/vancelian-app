"""Connexion admin par code e-mail (fallback passkey) — même JWT que /auth/login."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import AdminUser, AuthAdminEmailOtpChallenge, Person, get_db
from services.auth.device_attestation_service import DEVICE_TRUST_TRUSTED
from services.auth.account_policy import is_web_only_mobile_app_user
from services.auth.refresh_session import (
    LOGIN_FROZEN_DETAIL,
    MOBILE_APP_NOT_ALLOWED_DETAIL,
    _assert_user_not_security_locked,
    _auth_audit,
    issue_fresh_auth_session,
    normalize_device_id,
    _utcnow,
)
from services.security.login_auth_strategy_service import (
    decide_login_auth_strategy,
    persist_login_strategy_decision,
)
from services.auth.webauthn_config import is_admin_email_otp_enabled
from services.security.providers.email_provider import get_email_provider
from services.security.sms_otp_core import otp_plaintext_for_login_challenges
from services.security.two_factor_env import admin_email_otp_dev_code_for_response, is_production_like_env

logger = logging.getLogger("arquantix.auth.admin_email_otp")

router = APIRouter(prefix="/auth", tags=["auth-admin-email-otp"])

CODE_TTL_MINUTES = 5
MAX_ATTEMPTS = 5


def _validate_admin_login_email(v: str) -> str:
    """Identifiant e-mail login admin (accepte ``*.local`` et TLD de test ; pas ``EmailStr``)."""
    s = v.strip().lower()
    if "@" not in s or s.count("@") != 1:
        raise ValueError("invalid email address")
    local, domain = s.split("@", 1)
    if not local or not domain or ".." in local or ".." in domain:
        raise ValueError("invalid email address")
    return s


class AdminEmailOtpStartRequest(BaseModel):
    """E-mail admin : pas ``EmailStr`` (email-validator refuse p.ex. ``*.local`` en dev)."""

    email: str = Field(..., min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def _normalize_login_email(cls, v: str) -> str:
        return _validate_admin_login_email(v)


class AdminEmailOtpStartResponse(BaseModel):
    """Réponse uniforme (anti-énumération des comptes)."""

    status: str = "accepted"
    orchestrator: Optional[Dict[str, Any]] = None
    dev_code: Optional[str] = None


class AdminEmailOtpVerifyRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    code: str = Field(..., min_length=6, max_length=12)

    @field_validator("email")
    @classmethod
    def _normalize_login_email(cls, v: str) -> str:
        return _validate_admin_login_email(v)


def _normalize_email(s: str) -> str:
    return str(s).strip().lower()


def _hash_code(code: str) -> str:
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_code(code: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode("utf-8"), hashed.encode("ascii"))
    except Exception:  # noqa: BLE001
        return False


@router.post("/login/email-otp/start", response_model=AdminEmailOtpStartResponse)
def admin_email_otp_start(
    request: Request,
    body: AdminEmailOtpStartRequest,
    db: Session = Depends(get_db),
):
    if not is_admin_email_otp_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin email OTP login is disabled (set AUTH_ADMIN_EMAIL_OTP_ENABLED=true)",
        )
    email = _normalize_email(str(body.email))
    prov = get_email_provider()
    if prov.is_noop and is_production_like_env():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured (admin email OTP unavailable)",
        )

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if user is None:
        _auth_audit(
            "auth.admin_login.otp.start_unknown_email",
            db=None,
            request=request,
            user_id=None,
            device_id=normalize_device_id(request.headers.get("x-device-id")),
            metadata={"identifier_domain": email.split("@")[-1] if "@" in email else None},
            isolated=True,
        )
        return AdminEmailOtpStartResponse(dev_code=None)

    if is_web_only_mobile_app_user(user):
        _auth_audit(
            "auth.admin_login.otp.start_web_only_account",
            db=None,
            request=request,
            user_id=user.id,
            device_id=normalize_device_id(request.headers.get("x-device-id")),
            metadata={"identifier_domain": email.split("@")[-1] if "@" in email else None},
            isolated=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MOBILE_APP_NOT_ALLOWED_DETAIL,
        )

    if user.person_id is not None:
        pers = db.get(Person, user.person_id)
        if pers is not None and getattr(pers, "login_frozen", False):
            _auth_audit(
                "auth.admin_login.otp.start_login_frozen",
                db=None,
                request=request,
                user_id=user.id,
                device_id=normalize_device_id(request.headers.get("x-device-id")),
                metadata={"identifier_domain": email.split("@")[-1] if "@" in email else None},
                isolated=True,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LOGIN_FROZEN_DETAIL,
            )

    strat = decide_login_auth_strategy(
        db,
        request,
        user,
        device_header=request.headers.get("x-device-id"),
        attestation_trusted=False,
        login_channel="email_otp_start",
        login_identifier={"kind": "email", "value": email},
    )
    persist_login_strategy_decision(
        db,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        strategy=strat,
        action="auth.admin_login.otp.start_strategy",
    )
    if strat.blocked:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LOGIN_CONTEXT_BLOCKED",
                "message": "Connexion refusée pour ce contexte appareil (politique de sécurité).",
                "reason_codes": strat.reason_codes[:20],
            },
        )

    db.query(AuthAdminEmailOtpChallenge).filter(
        AuthAdminEmailOtpChallenge.email_normalized == email
    ).delete(synchronize_session=False)

    code = otp_plaintext_for_login_challenges()
    row = AuthAdminEmailOtpChallenge(
        email_normalized=email,
        code_hash=_hash_code(code),
        expires_at=_utcnow() + timedelta(minutes=CODE_TTL_MINUTES),
        attempt_count=0,
    )
    db.add(row)
    try:
        prov.send_otp(email, code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin email otp send failed: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send verification email",
        ) from exc

    _auth_audit(
        "auth.admin_login.otp.started",
        db=db,
        request=request,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        metadata={"identifier_domain": email.split("@")[-1] if "@" in email else None},
        isolated=False,
    )
    db.commit()
    orc_dict: Optional[Dict[str, Any]] = None
    if strat.context and isinstance(strat.context.get("adaptive_decision"), dict):
        orc_dict = dict(strat.context["adaptive_decision"])
    exposed = admin_email_otp_dev_code_for_response(code)
    return AdminEmailOtpStartResponse(orchestrator=orc_dict, dev_code=exposed)


@router.post("/login/email-otp/verify")
def admin_email_otp_verify(
    request: Request,
    body: AdminEmailOtpVerifyRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    if not is_admin_email_otp_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin email OTP login is disabled",
        )
    email = _normalize_email(str(body.email))
    code = str(body.code).strip()

    row = (
        db.query(AuthAdminEmailOtpChallenge)
        .filter(AuthAdminEmailOtpChallenge.email_normalized == email)
        .first()
    )
    if row is None or row.expires_at < _utcnow():
        if row is not None:
            db.delete(row)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code")

    if row.attempt_count >= MAX_ATTEMPTS:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Too many attempts")

    if not _verify_code(code, row.code_hash):
        row.attempt_count = int(row.attempt_count or 0) + 1
        db.commit()
        _auth_audit(
            "auth.admin_login.otp.verify_failed",
            db=None,
            request=request,
            user_id=None,
            device_id=normalize_device_id(x_device_id),
            metadata={"identifier_domain": email.split("@")[-1] if "@" in email else None},
            isolated=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code")

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if user is None:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code")

    _assert_user_not_security_locked(user)

    db.delete(row)
    db.commit()

    return issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=x_device_id,
        success_event_type="auth.admin_login.otp.succeeded",
        success_metadata={},
        device_trust_level=DEVICE_TRUST_TRUSTED,
        step_up_otp_required=False,
        auth_strength="otp",
    )
