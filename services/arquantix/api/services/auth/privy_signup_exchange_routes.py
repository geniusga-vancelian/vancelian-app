"""POST /auth/signup/privy/exchange — inscription par e-mail Privy (Person + AdminUser + session)."""
from __future__ import annotations

import secrets
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_password_hash
from database import AdminUser, Person, get_db
from services.auth.account_policy import is_web_only_mobile_app_user
from services.auth.device_attestation_service import DEVICE_TRUST_TRUSTED
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    DuplicateExternalIdentityError,
    get_person_from_external_identity,
    link_external_identity_to_person,
)
from services.auth.privy_exchange_routes import (
    PrivyExchangeRequest,
    PrivyExchangeResponse,
    _privy_verify_http_status,
    _serialize_active_wallets,
)
from services.auth.privy_token_verifier import (
    MODE_JWT,
    MODE_STUB,
    PrivyVerifyError,
    _exchange_mode,
    enrich_verified_privy_access,
    verify_privy_access_token,
)
from services.auth.refresh_session import LOGIN_FROZEN_DETAIL, issue_fresh_auth_session
from services.auth.security_setup_state import (
    ACCOUNT_STATE_ACTIVE,
    ACCOUNT_STATE_PARTIAL,
    derive_account_state,
)
from services.client_identity.service import ClientIdentityService
from services.customer_identity.profile_email import ensure_person_collected_email

router = APIRouter(prefix="/auth", tags=["auth-privy-signup"])


class PrivySignupExchangeRequest(PrivyExchangeRequest):
    """Corps identique à l’échange login ; ``email`` optionnel en mode stub dev uniquement."""

    email: Optional[str] = Field(
        None,
        description="Dev/stub uniquement si le jeton ne contient pas d’e-mail vérifié.",
    )


def _signup_email_blocked_detail_for_user(db: Session, user: AdminUser) -> Dict[str, Any]:
    state = derive_account_state(db, user)
    if state == ACCOUNT_STATE_PARTIAL:
        return {
            "code": "signup_email_use_login",
            "message": (
                "Cet e-mail est déjà associé à un compte en cours de sécurisation. "
                "Utilisez « Me connecter » pour finaliser le code d’accès."
            ),
            "account_state": state,
        }
    if state == ACCOUNT_STATE_ACTIVE:
        return {
            "code": "signup_email_unavailable",
            "message": (
                "Impossible de poursuivre cette inscription pour cet e-mail. "
                "Utilisez « Me connecter » ou une autre adresse."
            ),
            "account_state": state,
        }
    return {
        "code": "signup_email_unavailable",
        "message": (
            "Impossible de poursuivre cette inscription pour cet e-mail. "
            "Utilisez « Me connecter » ou une autre adresse."
        ),
    }


def _resolved_signup_email(
    verified_email: Optional[str],
    body_email: Optional[str],
) -> str:
    email = (verified_email or "").strip().lower()
    if email:
        return email
    if _exchange_mode() == MODE_STUB:
        stub_email = (body_email or "").strip().lower()
        if stub_email and "@" in stub_email:
            return stub_email
    # JWT : l’access token Privy n’embarque souvent pas l’e-mail ; le client envoie
    # l’adresse utilisée pour l’OTP (identity token ou API Privy restent prioritaires).
    fallback_email = (body_email or "").strip().lower()
    if _exchange_mode() == MODE_JWT and fallback_email and "@" in fallback_email:
        return fallback_email
    return ""


@router.post(
    "/signup/privy/exchange",
    response_model=PrivyExchangeResponse,
    summary="Inscription Privy → session JWT Vancelian (nouveau compte)",
)
def post_privy_signup_exchange(
    request: Request,
    body: PrivySignupExchangeRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> PrivyExchangeResponse:
    try:
        verified = verify_privy_access_token(body.privy_access_token or "")
        verified = enrich_verified_privy_access(
            verified,
            identity_token=body.privy_identity_token,
        )
    except PrivyVerifyError as exc:
        raise HTTPException(
            status_code=_privy_verify_http_status(exc.code),
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    email = _resolved_signup_email(verified.email, body.email)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "privy.signup.email_required",
                "message": "E-mail vérifié requis pour l’inscription.",
            },
        )

    privy_uid = verified.privy_user_id

    existing_person = get_person_from_external_identity(
        db, provider=PROVIDER_PRIVY, external_subject=privy_uid
    )
    if existing_person is not None:
        existing_user = (
            db.query(AdminUser)
            .filter(AdminUser.person_id == existing_person.id)
            .first()
        )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_signup_email_blocked_detail_for_user(db, existing_user),
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "signup_email_use_login",
                "message": "Compte déjà existant. Utilisez « Me connecter ».",
            },
        )

    conflict = db.query(AdminUser).filter(AdminUser.email == email).first()
    if conflict is not None:
        if is_web_only_mobile_app_user(conflict):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "MOBILE_APP_NOT_ALLOWED",
                    "message": "Ce compte n’est pas autorisé sur l’application mobile.",
                },
            )
        if getattr(conflict, "login_frozen", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LOGIN_FROZEN_DETAIL,
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_signup_email_blocked_detail_for_user(db, conflict),
        )

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
        email=email,
        hashed_password=get_password_hash(secrets.token_hex(32)),
        mobile_e164=None,
        person_id=person.id,
        mobile_app_allowed=True,
    )
    db.add(user)
    db.flush()

    ensure_person_collected_email(person, email)
    db.flush()

    try:
        link_external_identity_to_person(
            db,
            person_id=person.id,
            provider=PROVIDER_PRIVY,
            external_subject=privy_uid,
            external_email=email,
            external_phone=verified.phone,
        )
    except DuplicateExternalIdentityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "privy.signup.identity_conflict",
                "message": str(exc),
            },
        ) from exc

    ClientIdentityService.ensure_pe_client_for_login_user(
        db,
        person_id=person.id,
        client_email=email,
        actor_type="privy.signup.exchange",
        actor_id=privy_uid[:128],
    )
    db.flush()

    from services.auth.person_identity_bridge import get_pe_client_for_person
    from services.auth.privy_exchange_routes import (
        _persist_request_wallets,
        _resolve_exchange_wallets,
    )

    pe_client = get_pe_client_for_person(db, person_id=person.id)
    if pe_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "privy.signup.pe_client_missing",
                "message": "Client PE introuvable après création.",
            },
        )

    try:
        _persist_request_wallets(
            db,
            person_id=person.id,
            pe_client_id=pe_client.id,
            wallets=_resolve_exchange_wallets(body.wallets, verified.linked_wallets),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "privy.wallet_persist_error", "message": str(exc)},
        ) from exc

    tokens = issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=x_device_id,
        success_event_type="auth.signup.privy.exchange",
        success_metadata={
            "person_id": str(person.id),
            "privy_subject": privy_uid[:256],
        },
        device_trust_level=DEVICE_TRUST_TRUSTED,
        step_up_otp_required=False,
        auth_strength="oauth",
    )

    wallet_out = _serialize_active_wallets(db, person_id=person.id)

    return PrivyExchangeResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        token_type=tokens.get("token_type") or "bearer",
        device_id=tokens.get("device_id"),
        person_id=str(person.id),
        pe_client_id=str(pe_client.id),
        wallets=wallet_out,
    )
