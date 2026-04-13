"""Inscription mobile par SMS — même challenge OTP que la connexion, création compte + Person.

Endpoints : POST /auth/signup/sms/start, POST /auth/signup/sms/verify

- Si le numéro est déjà sur un **compte app** (``admin_users`` avec ``person_id``) : 403.
- Si le seul occupant est un **admin web** sans Person (``person_id`` NULL, pas d’app mobile) : le numéro
  n’est pas considéré comme « client » — l’inscription peut continuer (libération du mobile à la vérif).
  Ne pas confondre avec ``pe_clients`` : un seed peut avoir 0 client PE mais 1 ligne ``admin_users`` avec mobile.
- Si le numéro est libre : envoi SMS + challenge (comme login pour un utilisateur connu).
- Vérification : crée ``Person`` + ``AdminUser`` (e-mail placeholder unique), lie ``admin_users.person_id``.
"""
from __future__ import annotations

import logging
import secrets
import time
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from auth import get_password_hash
from database import AdminUser, AuthMobileLoginOtpChallenge, Person, get_db
from services.auth.mobile_otp_login_routes import (
    MobileLoginStartRequest,
    MobileLoginStartResponse,
    MobileLoginVerifyRequest,
    _apply_auth_mobile_otp_start_min_latency,
    _display_mask_for_subtitle,
    _effective_sms_provider,
    _normalize_phone_e164,
)
from services.auth.device_attestation_service import DEVICE_TRUST_TRUSTED
from services.auth.account_policy import app_signup_phone_blocked_by_existing_user
from services.auth.security_setup_state import (
    ACCOUNT_STATE_ACTIVE,
    ACCOUNT_STATE_PARTIAL,
    derive_account_state,
)
from services.auth.refresh_session import LOGIN_FROZEN_DETAIL, _utcnow, issue_fresh_auth_session
from services.customer_identity.profile_phone import ensure_person_collected_phone_e164
from services.auth.webauthn_config import is_mobile_otp_login_enabled
from services.security.masking import mask_phone_e164
from services.security.sms_otp_core import (
    SMS_CODE_TTL_MINUTES,
    SMS_MAX_VERIFY_ATTEMPTS,
    hash_sms_otp,
    new_plaintext_sms_otp,
    verify_sms_otp,
)
from services.security.two_factor_env import two_factor_dev_code_for_api_exposure
from services.security.two_factor_rate_limits import RESEND_SECONDS

logger = logging.getLogger("arquantix.auth.signup_mobile")

router = APIRouter(prefix="/auth", tags=["auth-mobile-signup"])


def _http_503_sms(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "sms_unavailable", "message": message},
    )


def _signup_blocked_detail() -> Dict[str, Any]:
    return {
        "code": "signup_phone_unavailable",
        "message": (
            "Impossible de poursuivre cette inscription pour ce numéro. "
            "Utilisez « Me connecter » ou un autre numéro."
        ),
    }


def _signup_blocked_detail_for_user(db: Session, user: AdminUser) -> Dict[str, Any]:
    """403 inscription : distingue compte PARTIAL (reprise login) vs ACTIVE (déjà client)."""
    state = derive_account_state(db, user)
    if state == ACCOUNT_STATE_PARTIAL:
        return {
            "code": "signup_phone_use_login",
            "message": (
                "Ce numéro est déjà associé à un compte en cours de sécurisation. "
                "Utilisez « Me connecter » pour finaliser le code d’accès."
            ),
            "account_state": state,
        }
    if state == ACCOUNT_STATE_ACTIVE:
        return {
            "code": "signup_phone_unavailable",
            "message": (
                "Impossible de poursuivre cette inscription pour ce numéro. "
                "Utilisez « Me connecter » ou un autre numéro."
            ),
            "account_state": state,
        }
    return {
        **_signup_blocked_detail(),
        "account_state": state,
    }


def _login_frozen_detail_if_user(db: Session, user: AdminUser) -> Optional[Dict[str, str]]:
    """Si la personne liée est gelée, retourne le même détail que le flux connexion (UX Flutter)."""
    pid = getattr(user, "person_id", None)
    if pid is None:
        return None
    p = db.get(Person, pid)
    if p is not None and getattr(p, "login_frozen", False):
        return dict(LOGIN_FROZEN_DETAIL)
    return None


def _find_person_by_collected_phone_e164(db: Session, phone: str):
    """Personne dont le profil EU / script contient déjà ce mobile (évite un 2e pe_client vide)."""
    row = db.execute(
        text(
            "SELECT id FROM persons WHERE (profile_json->'collected'->>'phone_e164') = :ph LIMIT 1"
        ),
        {"ph": phone},
    ).scalar()
    if row is None:
        return None
    return db.query(Person).filter(Person.id == row).first()


def _signup_sms_start_logic(
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

    existing_user = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
    if existing_user is not None and app_signup_phone_blocked_by_existing_user(existing_user):
        _apply_auth_mobile_otp_start_min_latency(t0)
        frozen_detail = _login_frozen_detail_if_user(db, existing_user)
        if frozen_detail is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=frozen_detail,
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_signup_blocked_detail_for_user(db, existing_user),
        )

    ch = (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
    )
    if ch is not None:
        delta = (_utcnow() - ch.created_at).total_seconds()
        if delta < RESEND_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "resend_rate_limited",
                    "message": f"Veuillez patienter {RESEND_SECONDS}s avant de redemander un code.",
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
        logger.warning("signup mobile otp sms send failed: %s", exc)
        db.rollback()
        raise _http_503_sms("Impossible d’envoyer le SMS. Réessayez plus tard.") from exc

    db.commit()
    dev = two_factor_dev_code_for_api_exposure()
    _apply_auth_mobile_otp_start_min_latency(t0)
    return MobileLoginStartResponse(
        masked_target=masked,
        resend_after_seconds=RESEND_SECONDS,
        dev_code=dev,
    )


def _signup_sms_verify_logic(
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_or_expired_code", "message": "Code incorrect ou expiré."},
        )

    conflict = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
    if conflict is not None:
        if app_signup_phone_blocked_by_existing_user(conflict):
            db.delete(row)
            db.commit()
            frozen_detail = _login_frozen_detail_if_user(db, conflict)
            if frozen_detail is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=frozen_detail,
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_signup_blocked_detail_for_user(db, conflict),
            )
        logger.info(
            "signup mobile: clearing mobile on web-only or orphan admin id=%s email=%s for first app signup",
            conflict.id,
            getattr(conflict, "email", None),
        )
        conflict.mobile_e164 = None
        db.flush()

    db.delete(row)
    db.flush()

    existing_profile_person = _find_person_by_collected_phone_e164(db, phone)
    if existing_profile_person is not None:
        if getattr(existing_profile_person, "login_frozen", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LOGIN_FROZEN_DETAIL,
            )
        existing_user_for_person = (
            db.query(AdminUser)
            .filter(AdminUser.person_id == existing_profile_person.id)
            .first()
        )
        if existing_user_for_person is not None:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_signup_blocked_detail_for_user(db, existing_user_for_person),
            )
        person = existing_profile_person
        logger.info(
            "signup mobile: reusing existing person %s for phone %s (avoid duplicate pe_client)",
            person.id,
            mask_phone_e164(phone),
        )
    else:
        person = Person(
            id=uuid.uuid4(),
            status="active",
            jurisdiction="EU",
            profile_json={"collected": {}, "computed": {}, "compliance": {}},
            kyc_status="not_started",
            account_state=ACCOUNT_STATE_PARTIAL,
        )
        db.add(person)
        db.flush()

    user = AdminUser(
        email=None,
        hashed_password=get_password_hash(secrets.token_hex(32)),
        mobile_e164=phone,
        person_id=person.id,
    )
    db.add(user)
    db.flush()

    # Customer 360 / profil mobile : téléphone canonique dans profile_json.collected
    # (admin_users.mobile_e164 = identifiant de connexion app, aligné ici).
    if ensure_person_collected_phone_e164(person, phone):
        db.flush()

    return issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=x_device_id,
        success_event_type="auth.signup.mobile.otp.succeeded",
        success_metadata={"person_id": str(person.id)},
        device_trust_level=DEVICE_TRUST_TRUSTED,
        step_up_otp_required=False,
        auth_strength="otp",
    )


@router.post("/signup/sms/start", response_model=MobileLoginStartResponse)
def signup_sms_start(
    request: Request,
    body: MobileLoginStartRequest,
    db: Session = Depends(get_db),
):
    return _signup_sms_start_logic(request, body, db)


@router.post("/signup/sms/verify")
def signup_sms_verify(
    request: Request,
    body: MobileLoginVerifyRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    return _signup_sms_verify_logic(request, body, db, x_device_id)
