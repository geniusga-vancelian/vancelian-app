"""Routes HTTP Passkeys / WebAuthn — intégration sessions Phase 2/3.1."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from schemas import (
    PasskeyLoginFinishRequest,
    PasskeyLoginStartRequest,
    PasskeyLoginStartResponse,
    PasskeyPromptRequest,
    PasskeyPublicItem,
    PasskeyRegisterFinishRequest,
    PasskeyRegisterFinishResponse,
    PasskeyRegisterStartBody,
    PasskeyRegisterStartResponse,
    PasskeyRevokeRequest,
    Token,
)
from services.auth import passkeys_service
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action

router = APIRouter(prefix="/auth/passkeys", tags=["auth-passkeys"])


def _dev(request: Request) -> str:
    return (request.headers.get("x-device-id") or "")[:128]


@router.post("/prompt", status_code=204)
def passkey_prompt(request: Request, body: PasskeyPromptRequest) -> Response:
    passkeys_service.record_passkey_prompt(
        request=request,
        event=body.event,
        identifier_domain=body.identifier_domain,
        detail=body.detail,
    )
    return Response(status_code=204)


@router.post("/register/start", response_model=PasskeyRegisterStartResponse)
def passkey_register_start(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("security_settings_change")),
    body: Optional[PasskeyRegisterStartBody] = None,
):
    try:
        out = passkeys_service.start_passkey_registration(
            db=db,
            request=request,
            user=current_user,
            device_label=body.device_label if body else None,
        )
    except HTTPException as e:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="security_settings_change",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"passkey_register_start:{e.status_code}",
        )
        db.commit()
        raise
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="security_settings_change",
        request=request,
        db=db,
        device_id=_dev(request),
        extra={"step": "passkey_register_start"},
    )
    db.commit()
    return PasskeyRegisterStartResponse(**out)


@router.post("/register/finish", response_model=PasskeyRegisterFinishResponse)
def passkey_register_finish(
    request: Request,
    payload: PasskeyRegisterFinishRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("security_settings_change")),
):
    try:
        out = passkeys_service.finish_passkey_registration(
            db=db,
            request=request,
            user=current_user,
            challenge_token=payload.challenge_token,
            credential=payload.credential,
            device_label=payload.device_label,
        )
    except HTTPException as e:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="security_settings_change",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"passkey_register_finish:{e.status_code}",
        )
        db.commit()
        raise
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="security_settings_change",
        request=request,
        db=db,
        device_id=_dev(request),
        extra={"step": "passkey_register_finish"},
    )
    db.commit()
    return PasskeyRegisterFinishResponse(**out)


@router.post("/login/start", response_model=PasskeyLoginStartResponse)
def passkey_login_start(
    request: Request,
    payload: PasskeyLoginStartRequest,
    db: Session = Depends(get_db),
):
    out = passkeys_service.start_passkey_login(db=db, request=request, email=str(payload.email))
    return PasskeyLoginStartResponse(**out)


@router.post("/login/finish", response_model=Token)
def passkey_login_finish(
    request: Request,
    payload: PasskeyLoginFinishRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    return passkeys_service.finish_passkey_login(
        db=db,
        request=request,
        challenge_token=payload.challenge_token,
        credential=payload.credential,
        device_header=x_device_id,
    )


@router.get("", response_model=List[PasskeyPublicItem])
def passkey_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
):
    rows = passkeys_service.list_passkeys(db=db, user=current_user)
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="view_sensitive_data",
        request=request,
        db=db,
        device_id=_dev(request),
        extra={"endpoint": "GET /auth/passkeys", "read_only": True},
    )
    db.commit()
    return [
        PasskeyPublicItem(
            id=r.id,
            credential_id=r.credential_id_b64,
            device_label=r.device_label,
            transports=r.transports_json,
            aaguid=r.aaguid,
            created_at=r.created_at,
            last_used_at=r.last_used_at,
        )
        for r in rows
    ]


@router.post("/revoke")
def passkey_revoke(
    request: Request,
    payload: PasskeyRevokeRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("security_settings_change")),
) -> Response:
    try:
        passkeys_service.revoke_passkey(
            db=db,
            request=request,
            user=current_user,
            credential_id=payload.credential_id,
        )
    except HTTPException as e:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="security_settings_change",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"passkey_revoke:{e.status_code}",
        )
        db.commit()
        raise
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="security_settings_change",
        request=request,
        db=db,
        device_id=_dev(request),
        extra={"step": "passkey_revoke"},
    )
    db.commit()
    return Response(status_code=204)
