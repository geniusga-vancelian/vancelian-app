"""
Passkeys / WebAuthn (Phase 3.2) — clés privées uniquement côté authenticator.

Dépend de ``webauthn`` ; configuration ``WEBAUTHN_RP_ID``, ``WEBAUTHN_RP_NAME``, ``WEBAUTHN_ORIGINS``.
"""
from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    UserVerificationRequirement,
)

from database import AdminUser, AuthPasskey, AuthWebAuthnChallenge, Person
from services.auth.account_policy import is_web_only_mobile_app_user
from services.auth.device_attestation_service import DEVICE_TRUST_TRUSTED
from services.auth.refresh_session import (
    LOGIN_FROZEN_DETAIL,
    MOBILE_APP_NOT_ALLOWED_DETAIL,
    _auth_audit,
    issue_fresh_auth_session,
    normalize_device_id,
    _utcnow,
)
from services.auth.webauthn_config import (
    get_webauthn_settings,
    is_passkeys_enabled,
    webauthn_challenge_ttl_sec,
)

logger = logging.getLogger("arquantix.auth.passkeys")

FLOW_REGISTER = "register"
FLOW_LOGIN = "login"

_PROMPT_EVENTS = frozenset(
    {
        "auth.passkey.prompt.opened",
        "auth.passkey.prompt.cancelled",
        "auth.passkey.prompt.failed",
        # Auto-trigger passkey (login téléphone) — analytics / SIEM, même transport /prompt.
        "auth.login.passkey_auto_triggered",
        "auth.login.passkey_auto_trigger_cancelled",
        "auth.login.passkey_auto_trigger_failed",
        "auth.login.passkey_auto_trigger_fallback_otp",
    }
)


def _require_passkeys() -> None:
    if not is_passkeys_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Passkeys disabled")


def _rp_config() -> tuple[str, str, List[str]]:
    s = get_webauthn_settings()
    return s.rp_id, s.rp_name, s.origins


def _webauthn_user_handle(user_id: int) -> bytes:
    raw = f"arq-admin:{user_id}".encode("utf-8")
    return raw if len(raw) <= 64 else raw[:64]


def _normalize_email(s: str) -> str:
    return str(s).strip().lower()


def _passkey_challenge_identifier(user: AdminUser) -> str:
    """Identifiant stable pour challenge passkey (PR4 : email nullable)."""
    em = getattr(user, "email", None)
    if em and str(em).strip():
        return _normalize_email(str(em))
    mob = getattr(user, "mobile_e164", None)
    if mob and str(mob).strip():
        return f"tel:{str(mob).strip()}"
    return f"uid:{user.id}"


def _exclude_credentials_for_user(db: Session, user_id: int) -> List[PublicKeyCredentialDescriptor]:
    rows = (
        db.query(AuthPasskey)
        .filter(AuthPasskey.user_id == user_id, AuthPasskey.revoked_at.is_(None))
        .all()
    )
    out: List[PublicKeyCredentialDescriptor] = []
    for r in rows:
        try:
            cid = base64url_to_bytes(r.credential_id_b64)
        except Exception:  # noqa: BLE001
            continue
        out.append(
            PublicKeyCredentialDescriptor(
                id=cid,
                type=PublicKeyCredentialType.PUBLIC_KEY,
            )
        )
    return out


def _allow_credentials_for_user(db: Session, user_id: int) -> List[PublicKeyCredentialDescriptor]:
    return _exclude_credentials_for_user(db, user_id)


def _store_challenge(
    db: Session,
    *,
    challenge_b64: str,
    flow_type: str,
    user_id: Optional[int],
    identifier: Optional[str],
) -> uuid.UUID:
    tid = uuid.uuid4()
    row = AuthWebAuthnChallenge(
        id=tid,
        challenge_b64=challenge_b64,
        flow_type=flow_type,
        user_id=user_id,
        identifier=identifier,
        expires_at=_utcnow() + timedelta(seconds=webauthn_challenge_ttl_sec()),
    )
    db.add(row)
    db.flush()
    return tid


def _load_challenge(db: Session, challenge_token: uuid.UUID) -> AuthWebAuthnChallenge:
    row = db.get(AuthWebAuthnChallenge, challenge_token)
    if row is None or row.expires_at < _utcnow():
        if row is not None:
            db.delete(row)
            db.flush()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge")
    return row


def start_passkey_registration(
    *,
    db: Session,
    request: Request,
    user: AdminUser,
    device_label: Optional[str],
) -> Dict[str, Any]:
    _require_passkeys()
    rp_id, rp_name, _ = _rp_config()
    challenge_bytes = secrets.token_bytes(32)
    exclude = _exclude_credentials_for_user(db, user.id)
    _pid = _passkey_challenge_identifier(user)
    opts = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_name=_pid,
        user_id=_webauthn_user_handle(user.id),
        user_display_name=_pid,
        challenge=challenge_bytes,
        timeout=120_000,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=exclude or None,
    )
    options_json = json.loads(options_to_json(opts))
    ch_b64 = options_json["challenge"]
    token = _store_challenge(
        db,
        challenge_b64=ch_b64,
        flow_type=FLOW_REGISTER,
        user_id=user.id,
        identifier=_passkey_challenge_identifier(user),
    )
    _auth_audit(
        "auth.passkey.register.started",
        db=db,
        request=request,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        metadata={"device_label": device_label},
        isolated=False,
    )
    db.commit()
    return {"options": options_json, "challenge_token": str(token)}


def finish_passkey_registration(
    *,
    db: Session,
    request: Request,
    user: AdminUser,
    challenge_token: str,
    credential: Dict[str, Any],
    device_label: Optional[str],
) -> Dict[str, str]:
    _require_passkeys()
    rp_id, _, origins = _rp_config()
    try:
        tid = uuid.UUID(challenge_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid challenge_token") from exc
    ch = _load_challenge(db, tid)
    if ch.flow_type != FLOW_REGISTER or ch.user_id != user.id:
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=400, detail="Challenge mismatch")
    expected_challenge = base64url_to_bytes(ch.challenge_b64)
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=origins,
            require_user_verification=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("passkey register verify failed: %s", exc)
        _auth_audit(
            "auth.passkey.register.failed",
            db=None,
            request=request,
            user_id=user.id,
            device_id=normalize_device_id(request.headers.get("x-device-id")),
            metadata={"reason": str(exc)[:200]},
            isolated=True,
        )
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=400, detail="Passkey registration verification failed") from exc

    cid_b64 = bytes_to_base64url(verified.credential_id)
    pk_b64 = bytes_to_base64url(verified.credential_public_key)
    existing = db.query(AuthPasskey).filter(AuthPasskey.credential_id_b64 == cid_b64).first()
    if existing is not None:
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=409, detail="Credential already registered")

    transports = None
    resp = credential.get("response") if isinstance(credential, dict) else None
    if isinstance(resp, dict) and resp.get("transports"):
        transports = resp.get("transports")

    row = AuthPasskey(
        id=uuid.uuid4(),
        user_id=user.id,
        credential_id_b64=cid_b64,
        public_key_b64=pk_b64,
        sign_count=verified.sign_count,
        transports_json=transports,
        device_label=(device_label or None)[:255] if device_label else None,
        aaguid=(verified.aaguid or None)[:64] if verified.aaguid else None,
    )
    db.add(row)
    db.delete(ch)
    _auth_audit(
        "auth.passkey.register.succeeded",
        db=db,
        request=request,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        metadata={"credential_id_prefix": cid_b64[:12]},
        isolated=False,
    )
    db.commit()
    return {"credential_id": cid_b64, "status": "ok"}


def start_passkey_login(
    *,
    db: Session,
    request: Request,
    email: str,
) -> Dict[str, Any]:
    _require_passkeys()
    rp_id, _, _ = _rp_config()
    ident = _normalize_email(email)
    user = db.query(AdminUser).filter(AdminUser.email == ident).first()
    if user is not None and is_web_only_mobile_app_user(user):
        _auth_audit(
            "auth.passkey.login.start_web_only_account",
            db=None,
            request=request,
            user_id=user.id,
            device_id=normalize_device_id(request.headers.get("x-device-id")),
            metadata={"identifier_domain": ident.split("@")[-1] if "@" in ident else None},
            isolated=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MOBILE_APP_NOT_ALLOWED_DETAIL,
        )
    if user is not None and user.person_id is not None:
        pers = db.get(Person, user.person_id)
        if pers is not None and getattr(pers, "login_frozen", False):
            _auth_audit(
                "auth.passkey.login.start_login_frozen",
                db=None,
                request=request,
                user_id=user.id,
                device_id=normalize_device_id(request.headers.get("x-device-id")),
                metadata={"identifier_domain": ident.split("@")[-1] if "@" in ident else None},
                isolated=True,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LOGIN_FROZEN_DETAIL,
            )
    allow: Optional[List[PublicKeyCredentialDescriptor]] = None
    uid: Optional[int] = None
    if user is not None:
        uid = user.id
        allow = _allow_credentials_for_user(db, user.id)
        if not allow:
            user = None
            uid = None
            allow = None

    if user is not None and uid is not None and allow:
        try:
            from services.auth.adaptive_auth_orchestrator import (
                is_adaptive_auth_enabled,
                orchestrate_login_strategy_from_request,
                persist_adaptive_auth_decision,
            )

            if is_adaptive_auth_enabled():
                dec, _ = orchestrate_login_strategy_from_request(
                    db,
                    request,
                    user,
                    device_header=request.headers.get("x-device-id"),
                    login_identifier={"kind": "email", "value": ident},
                    login_channel="passkey_start",
                    attestation_trusted=False,
                )
                persist_adaptive_auth_decision(
                    db,
                    user_id=user.id,
                    device_id=normalize_device_id(request.headers.get("x-device-id")),
                    decision=dec,
                    login_channel="passkey_start",
                )
                if dec.blocked:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": "LOGIN_ORCHESTRATOR_BLOCKED",
                            "message": "Connexion refusée (politique adaptative).",
                            "reason_codes": dec.reason_codes[:20],
                        },
                    )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("passkey start adaptive orchestrator skipped: %s", exc)

    challenge_bytes = secrets.token_bytes(32)
    opts = generate_authentication_options(
        rp_id=rp_id,
        challenge=challenge_bytes,
        timeout=120_000,
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    options_json = json.loads(options_to_json(opts))
    ch_b64 = options_json["challenge"]
    token = _store_challenge(
        db,
        challenge_b64=ch_b64,
        flow_type=FLOW_LOGIN,
        user_id=uid,
        identifier=ident,
    )
    _auth_audit(
        "auth.passkey.login.started",
        db=db,
        request=request,
        user_id=uid,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        metadata={"identifier_domain": ident.split("@")[-1] if "@" in ident else None},
        isolated=False,
    )
    db.commit()
    return {"options": options_json, "challenge_token": str(token)}


def finish_passkey_login(
    *,
    db: Session,
    request: Request,
    challenge_token: str,
    credential: Dict[str, Any],
    device_header: Optional[str],
) -> Dict[str, str]:
    _require_passkeys()
    rp_id, _, origins = _rp_config()
    try:
        tid = uuid.UUID(challenge_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid challenge_token") from exc
    ch = _load_challenge(db, tid)
    if ch.flow_type != FLOW_LOGIN:
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=400, detail="Challenge mismatch")

    raw_id = credential.get("rawId")
    if not raw_id:
        _auth_audit(
            "auth.passkey.login.failed",
            db=None,
            request=request,
            user_id=ch.user_id,
            device_id=normalize_device_id(device_header),
            metadata={"reason": "missing_rawId"},
            isolated=True,
        )
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=400, detail="Missing credential rawId")

    if isinstance(raw_id, str):
        try:
            cid_bytes = base64url_to_bytes(raw_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Invalid rawId") from exc
    else:
        raise HTTPException(status_code=400, detail="Invalid rawId type")
    cid_b64 = bytes_to_base64url(cid_bytes)

    pk_row = (
        db.query(AuthPasskey)
        .filter(
            AuthPasskey.credential_id_b64 == cid_b64,
            AuthPasskey.revoked_at.is_(None),
        )
        .first()
    )
    if pk_row is None:
        _auth_audit(
            "auth.passkey.login.failed",
            db=None,
            request=request,
            user_id=ch.user_id,
            device_id=normalize_device_id(device_header),
            metadata={"reason": "unknown_credential"},
            isolated=True,
        )
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=401, detail="Unknown passkey")

    user = db.get(AdminUser, pk_row.user_id)
    if user is None:
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=401, detail="User not found")

    if ch.identifier and _passkey_challenge_identifier(user) != ch.identifier:
        _auth_audit(
            "auth.passkey.login.failed",
            db=None,
            request=request,
            user_id=user.id,
            device_id=normalize_device_id(device_header),
            metadata={"reason": "email_mismatch"},
            isolated=True,
        )
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=401, detail="Passkey login failed")

    if ch.user_id is not None and ch.user_id != user.id:
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=401, detail="Passkey login failed")

    expected_challenge = base64url_to_bytes(ch.challenge_b64)
    try:
        pub = base64url_to_bytes(pk_row.public_key_b64)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Stored public key invalid") from exc

    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=origins,
            credential_public_key=pub,
            credential_current_sign_count=int(pk_row.sign_count or 0),
            require_user_verification=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("passkey login verify failed: %s", exc)
        _auth_audit(
            "auth.passkey.login.failed",
            db=None,
            request=request,
            user_id=user.id,
            device_id=normalize_device_id(device_header),
            metadata={"reason": str(exc)[:200]},
            isolated=True,
        )
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=401, detail="Passkey assertion invalid") from exc

    if verified.new_sign_count <= int(pk_row.sign_count or 0):
        _auth_audit(
            "auth.passkey.login.failed",
            db=None,
            request=request,
            user_id=user.id,
            device_id=normalize_device_id(device_header),
            metadata={"reason": "sign_count_stale"},
            isolated=True,
        )
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=401, detail="Passkey rejected")

    pk_row.sign_count = verified.new_sign_count
    pk_row.last_used_at = _utcnow()
    db.delete(ch)
    return issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=device_header,
        success_event_type="auth.passkey.login.succeeded",
        success_metadata={"credential_id_prefix": cid_b64[:12]},
        device_trust_level=DEVICE_TRUST_TRUSTED,
        step_up_otp_required=False,
        auth_strength="passkey",
    )


def list_passkeys(*, db: Session, user: AdminUser) -> List[AuthPasskey]:
    _require_passkeys()
    return (
        db.query(AuthPasskey)
        .filter(AuthPasskey.user_id == user.id, AuthPasskey.revoked_at.is_(None))
        .order_by(AuthPasskey.created_at.desc())
        .all()
    )


def revoke_passkey(
    *,
    db: Session,
    request: Request,
    user: AdminUser,
    credential_id: str,
) -> None:
    _require_passkeys()
    cid = str(credential_id).strip()
    row = (
        db.query(AuthPasskey)
        .filter(
            AuthPasskey.user_id == user.id,
            AuthPasskey.credential_id_b64 == cid,
            AuthPasskey.revoked_at.is_(None),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Passkey not found")
    row.revoked_at = _utcnow()
    _auth_audit(
        "auth.passkey.revoked",
        db=db,
        request=request,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        metadata={"credential_id_prefix": cid[:12]},
        isolated=False,
    )
    db.commit()


def record_passkey_prompt(
    *,
    request: Request,
    event: str,
    identifier_domain: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """Événements UX prompt passkey (mobile) — audit isolé, ne bloque pas le flux."""
    if not is_passkeys_enabled():
        return
    et = (event or "").strip()
    if et not in _PROMPT_EVENTS:
        raise HTTPException(status_code=400, detail="Invalid event")
    meta: Dict[str, Any] = {}
    if identifier_domain:
        meta["identifier_domain"] = identifier_domain[:255]
    if detail:
        meta["detail"] = detail[:200]
    _auth_audit(
        et,
        db=None,
        request=request,
        user_id=None,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        metadata=meta or None,
        isolated=True,
    )
