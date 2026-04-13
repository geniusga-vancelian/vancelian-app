"""Connexion admin par OTP SMS — même cœur OTP que la 2FA / registration (sms_otp_core + provider SMS).

Endpoints canoniques : POST /auth/login/sms/start, POST /auth/login/sms/verify.
Alias historiques : POST /auth/login/start, POST /auth/login/verify.
"""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import AdminUser, AuthMobileLoginOtpChallenge, Person, get_db
from services.auth.account_policy import is_web_only_mobile_app_user
from services.auth.security_setup_state import (
    ACCOUNT_STATE_ACTIVE,
    derive_account_state,
)
from services.auth.device_attestation_service import DEVICE_TRUST_TRUSTED
from services.auth.device_fingerprint import is_device_fingerprint_enabled, parse_device_fingerprint_header
from services.auth.refresh_session import (
    _assert_user_not_security_locked,
    _auth_audit,
    issue_fresh_auth_session,
    normalize_device_id,
    _utcnow,
)
from services.security.device_reputation.device_reputation_service import resolve_device_hash_from_request
from services.security.login_auth_strategy_service import (
    decide_login_auth_strategy,
    persist_login_strategy_decision,
)
from services.security.login_device_trust_service import (
    is_login_device_trust_enabled,
    update_user_device_profile_on_login,
)
from services.auth.passkey_login_eligibility import (
    evaluate_passkey_login_eligibility,
    should_expose_passkey_email_for_auto,
)
from services.auth.webauthn_config import is_mobile_otp_login_enabled
from services.security.masking import mask_phone_e164
from services.security.providers import get_sms_provider
from services.security.providers.fake_sms_provider import FakeSmsProvider
from services.security.sms_otp_core import (
    SMS_CODE_TTL_MINUTES,
    SMS_MAX_VERIFY_ATTEMPTS,
    hash_sms_otp,
    new_plaintext_sms_otp,
    verify_sms_otp,
)
from services.security.two_factor_env import is_two_factor_relaxed, two_factor_dev_code_for_api_exposure
from services.security.two_factor_rate_limits import RESEND_SECONDS

logger = logging.getLogger("arquantix.auth.mobile_otp_login")

router = APIRouter(prefix="/auth", tags=["auth-mobile-otp-login"])


def _apply_auth_mobile_otp_start_min_latency(t0: float) -> None:
    """Réduit l’énumération par timing entre numéro connu (envoi SMS) et inconnu (pas d’envoi).

    ``AUTH_MOBILE_OTP_START_MIN_LATENCY_MS`` : durée minimale de réponse pour les **200**
    ``MobileLoginStartResponse`` uniquement (pas les 429/503). 0 ou absent = désactivé.
    """
    raw = (os.getenv("AUTH_MOBILE_OTP_START_MIN_LATENCY_MS") or "").strip()
    if not raw:
        return
    try:
        min_ms = int(raw)
    except ValueError:
        logger.warning("AUTH_MOBILE_OTP_START_MIN_LATENCY_MS invalid: %r", raw)
        return
    if min_ms <= 0:
        return
    elapsed_ms = (time.perf_counter() - t0) * 1000
    need_ms = min_ms - elapsed_ms
    if need_ms > 0:
        time.sleep(need_ms / 1000.0)


class MobileLoginStartRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=32, description="E.164, ex. +33612345678")


class MobileLoginStartResponse(BaseModel):
    status: str = "accepted"
    masked_target: str
    resend_after_seconds: int = RESEND_SECONDS
    dev_code: Optional[str] = None
    # Indices UX / clients — la politique d’exécution reste côté session (issue_fresh_auth_session).
    auth_strategy_hint: Optional[str] = None
    primary_auth_method: Optional[str] = None
    step_up_recommended: Optional[bool] = None
    # Contrat auto-trigger passkey (fast lane) — OTP reste toujours possible.
    recommended_auth_method: Optional[str] = None  # "passkey" | "otp"
    fallback_auth_method: Optional[str] = None
    step_up_required: Optional[bool] = None
    device_trust_level: Optional[str] = None
    passkey_auto_eligible: Optional[bool] = None
    passkey_login_email: Optional[str] = None
    # Décision Adaptive Auth (si ``ADAPTIVE_AUTH_ENABLED``) — source-of-truth UX.
    orchestrator: Optional[Dict[str, Any]] = None
    account_state: Optional[str] = Field(
        default=None,
        description="ACTIVE, PARTIAL, INCOMPLETE — compte app connu (mobile trouvé en base).",
    )
    resume_registration_hint: Optional[bool] = Field(
        default=None,
        description="True si le compte n'est pas encore ACTIVE (reprise login / finalisation).",
    )
    sms_otp_dispatched: bool = Field(
        default=False,
        description="True si un défi OTP a été créé et un SMS envoyé (siné numéro inconnu / web-only / gel).",
    )


class MobileLoginVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=32)
    code: str = Field(..., min_length=6, max_length=12)


def _normalize_phone_e164(raw: str) -> str:
    t = re.sub(r"\s+", "", (raw or "").strip())
    if not t:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "phone_required", "message": "Numéro de mobile requis."},
        )
    if not t.startswith("+"):
        t = "+" + t.lstrip("+")
    return t


def _display_mask_for_subtitle(phone_normalized: str) -> str:
    p = phone_normalized.strip()
    if len(p) < 5:
        return mask_phone_e164(p) or "***"
    tail = p[-2:]
    prefix_len = min(4, max(1, len(p) - 2))
    head = p[:prefix_len]
    return f"{head} ••••••{tail}"


def _effective_sms_provider(request: Request):
    """Même chaîne que get_sms_provider() ; en env relaxed, FakeSmsProvider si Twilio absent (comme besoin dev)."""
    sms = get_sms_provider()
    if not getattr(sms, "is_noop", False):
        return sms
    relaxed = is_two_factor_relaxed(app_testing=getattr(request.app.state, "testing", False))
    if relaxed:
        return FakeSmsProvider()
    return sms


def _http_503_sms(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "sms_unavailable", "message": message},
    )


def _mobile_login_start_logic(
    request: Request,
    body: MobileLoginStartRequest,
    db: Session,
) -> MobileLoginStartResponse:
    if not is_mobile_otp_login_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "feature_disabled",
                "message": "Connexion par SMS désactivée sur ce serveur.",
            },
        )

    phone = _normalize_phone_e164(body.phone)
    masked = _display_mask_for_subtitle(phone)
    t0 = time.perf_counter()
    sms = _effective_sms_provider(request)
    if getattr(sms, "is_noop", False):
        raise _http_503_sms(
            "Envoi SMS indisponible (configurez Twilio ou FAKE_SMS_PROVIDER en développement).",
        )

    user = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
    if user is None:
        _auth_audit(
            "auth.mobile_login.otp.start_unknown_phone",
            db=None,
            request=request,
            user_id=None,
            device_id=normalize_device_id(request.headers.get("x-device-id")),
            metadata={"masked": mask_phone_e164(phone)},
            isolated=True,
        )
        _apply_auth_mobile_otp_start_min_latency(t0)
        return MobileLoginStartResponse(
            masked_target=masked,
            resend_after_seconds=RESEND_SECONDS,
            sms_otp_dispatched=False,
        )

    # Compte réservé au back-office web : pas d’OTP / pas de session app (même réponse qu’un numéro inconnu).
    if is_web_only_mobile_app_user(user):
        _auth_audit(
            "auth.mobile_login.otp.start_web_only_account",
            db=None,
            request=request,
            user_id=user.id,
            device_id=normalize_device_id(request.headers.get("x-device-id")),
            metadata={"masked": mask_phone_e164(phone)},
            isolated=True,
        )
        _apply_auth_mobile_otp_start_min_latency(t0)
        return MobileLoginStartResponse(
            masked_target=masked,
            resend_after_seconds=RESEND_SECONDS,
            sms_otp_dispatched=False,
        )

    if user.person_id is not None:
        pers = db.get(Person, user.person_id)
        if pers is not None and getattr(pers, "login_frozen", False):
            _auth_audit(
                "auth.mobile_login.otp.start_login_frozen",
                db=None,
                request=request,
                user_id=user.id,
                device_id=normalize_device_id(request.headers.get("x-device-id")),
                metadata={"masked": mask_phone_e164(phone)},
                isolated=True,
            )
            _apply_auth_mobile_otp_start_min_latency(t0)
            return MobileLoginStartResponse(
                masked_target=masked,
                resend_after_seconds=RESEND_SECONDS,
                sms_otp_dispatched=False,
            )

    existing = (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
    )
    if existing is not None:
        delta = (_utcnow() - existing.created_at).total_seconds()
        if delta < RESEND_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "resend_rate_limited",
                    "message": f"Veuillez patienter {RESEND_SECONDS}s avant de redemander un code.",
                },
            )

    strat = decide_login_auth_strategy(
        db,
        request,
        user,
        device_header=request.headers.get("x-device-id"),
        attestation_trusted=False,
        login_channel="sms_start",
    )
    persist_login_strategy_decision(
        db,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        strategy=strat,
        action="auth.mobile_login.otp.start_strategy",
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

    db.query(AuthMobileLoginOtpChallenge).filter(
        AuthMobileLoginOtpChallenge.phone_e164_normalized == phone
    ).delete(synchronize_session=False)

    code = new_plaintext_sms_otp()
    row = AuthMobileLoginOtpChallenge(
        id=uuid.uuid4(),
        phone_e164_normalized=phone,
        code_hash=hash_sms_otp(code),
        expires_at=_utcnow() + timedelta(minutes=SMS_CODE_TTL_MINUTES),
        attempt_count=0,
    )
    db.add(row)
    try:
        sms.send_otp(phone, code, challenge_id=str(row.id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("mobile login otp sms send failed: %s", exc)
        db.rollback()
        raise _http_503_sms("Impossible d’envoyer le SMS. Réessayez plus tard.") from exc

    risk = strat.context.get("risk") if strat.context else None
    hint = risk.get("decision_hint") if isinstance(risk, dict) else None
    risk_d: Dict[str, Any] = risk if isinstance(risk, dict) else {}
    dev_ctx: Dict[str, Any] = {
        "device_id": strat.context.get("device_id") if strat.context else None,
        "device_hash": strat.context.get("device_hash") if strat.context else None,
    }
    elig = evaluate_passkey_login_eligibility(
        db,
        user,
        device_context=dev_ctx,
        risk_context=risk_d,
        step_up_required=bool(strat.step_up_required),
    )
    orc_dict: Optional[Dict[str, Any]] = None
    if strat.context and isinstance(strat.context.get("adaptive_decision"), dict):
        orc_dict = dict(strat.context["adaptive_decision"])  # copie JSON-safe
    if orc_dict:
        if (
            orc_dict.get("primary_method") == "passkey"
            and orc_dict.get("auto_trigger_passkey")
        ):
            rec_method = "passkey"
        else:
            rec_method = "otp"
    else:
        rec_method = "passkey" if elig.recommended else "otp"
    pk_email = None
    if rec_method == "passkey" and should_expose_passkey_email_for_auto():
        pk_email = (user.email or "").strip().lower() or None

    _auth_audit(
        "auth.mobile_login.otp.started",
        db=db,
        request=request,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        metadata={
            "masked": mask_phone_e164(phone),
            "passkey_auto_recommended": elig.recommended,
            "recommended_auth_method": rec_method,
        },
        isolated=False,
    )
    db.commit()
    dev = two_factor_dev_code_for_api_exposure()
    _apply_auth_mobile_otp_start_min_latency(t0)
    acct = derive_account_state(db, user)
    resume = acct != ACCOUNT_STATE_ACTIVE
    return MobileLoginStartResponse(
        masked_target=masked,
        resend_after_seconds=RESEND_SECONDS,
        dev_code=dev,
        auth_strategy_hint=hint,
        primary_auth_method=rec_method,
        step_up_recommended=strat.step_up_required,
        recommended_auth_method=rec_method,
        fallback_auth_method="otp",
        step_up_required=strat.step_up_required,
        device_trust_level=strat.device_trust_level,
        passkey_auto_eligible=elig.eligible,
        passkey_login_email=pk_email,
        orchestrator=orc_dict,
        account_state=acct,
        resume_registration_hint=resume,
        sms_otp_dispatched=True,
    )


def _mobile_login_verify_logic(
    request: Request,
    body: MobileLoginVerifyRequest,
    db: Session,
    x_device_id: Optional[str],
) -> Dict[str, Any]:
    if not is_mobile_otp_login_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "feature_disabled", "message": "Connexion par SMS désactivée."},
        )
    phone = _normalize_phone_e164(body.phone)
    code = str(body.code).strip()

    row = (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
    )
    if row is None or row.expires_at < _utcnow():
        if row is not None:
            db.delete(row)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_or_expired_code", "message": "Code incorrect ou expiré."},
        )

    if row.attempt_count >= SMS_MAX_VERIFY_ATTEMPTS:
        db.delete(row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "too_many_attempts",
                "message": "Trop de tentatives. Demandez un nouveau code.",
            },
        )

    if not verify_sms_otp(code, row.code_hash):
        row.attempt_count = int(row.attempt_count or 0) + 1
        db.commit()
        if is_login_device_trust_enabled():
            u_fail = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
            if u_fail is not None:
                did_f = normalize_device_id(x_device_id)
                _, fh_f = parse_device_fingerprint_header(request.headers.get("x-device-fingerprint"))
                if not is_device_fingerprint_enabled():
                    fh_f = None
                dh_f = resolve_device_hash_from_request(request, did_f, fh_f)
                ip_f = request.client.host if request.client else None

                def _c_f() -> Optional[str]:
                    for h in ("cf-ipcountry", "CF-IPCountry", "x-geo-country", "X-Geo-Country"):
                        v = request.headers.get(h)
                        if v and str(v).strip():
                            return str(v).strip()[:8]
                    return None

                update_user_device_profile_on_login(
                    db,
                    user=u_fail,
                    device_hash=dh_f,
                    device_id_normalized=did_f,
                    fingerprint_hash=fh_f,
                    ip_address=ip_f,
                    country_code=_c_f(),
                    success=False,
                    auth_strength="otp",
                    attestation_trusted=False,
                )
                db.commit()
        _auth_audit(
            "auth.mobile_login.otp.verify_failed",
            db=None,
            request=request,
            user_id=None,
            device_id=normalize_device_id(x_device_id),
            metadata={"masked": mask_phone_e164(phone)},
            isolated=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_or_expired_code", "message": "Code incorrect ou expiré."},
        )

    user = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
    if user is None:
        db.delete(row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_or_expired_code", "message": "Code incorrect ou expiré."},
        )

    _assert_user_not_security_locked(user)

    # Aligner le profil customer (CMS / Customer 360) si seul admin_users avait le mobile.
    if user.person_id is not None:
        from database import Person

        person = db.get(Person, user.person_id)
        if person is not None:
            from services.customer_identity.profile_phone import ensure_person_collected_phone_e164

            if ensure_person_collected_phone_e164(person, phone):
                db.flush()

    db.delete(row)
    db.commit()

    return issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=x_device_id,
        success_event_type="auth.mobile_login.otp.succeeded",
        success_metadata={},
        device_trust_level=DEVICE_TRUST_TRUSTED,
        step_up_otp_required=False,
        auth_strength="otp",
    )


@router.post("/login/sms/start", response_model=MobileLoginStartResponse)
def mobile_login_sms_start(
    request: Request,
    body: MobileLoginStartRequest,
    db: Session = Depends(get_db),
):
    return _mobile_login_start_logic(request, body, db)


@router.post("/login/start", response_model=MobileLoginStartResponse)
def mobile_login_start_legacy(
    request: Request,
    body: MobileLoginStartRequest,
    db: Session = Depends(get_db),
):
    """Alias historique — préférer /auth/login/sms/start."""
    return _mobile_login_start_logic(request, body, db)


@router.post("/login/sms/verify")
def mobile_login_sms_verify(
    request: Request,
    body: MobileLoginVerifyRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    return _mobile_login_verify_logic(request, body, db, x_device_id)


@router.post("/login/verify")
def mobile_login_verify_legacy(
    request: Request,
    body: MobileLoginVerifyRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """Alias historique — préférer /auth/login/sms/verify."""
    return _mobile_login_verify_logic(request, body, db, x_device_id)
