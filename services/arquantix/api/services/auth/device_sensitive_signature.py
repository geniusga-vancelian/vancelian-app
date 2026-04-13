"""PR D3 — dépendance FastAPI : signature device + nonce pour routes sensibles."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import AdminUser, AuthDeviceCredential, get_db
from services.auth.device_pr_d3_policy import (
    device_signature_nonce_ttl_sec,
    sensitive_routes_device_signature_enabled,
)
from services.auth.device_pr_d4_policy import device_risk_checks_enabled, nonce_route_scoping_enabled
from services.auth.device_request_signature import verify_sensitive_device_signature
from services.auth.device_risk_pr_d4 import evaluate_sensitive_route_risk
from services.auth.device_sensitive_action_velocity import record_sensitive_action
from services.auth.device_signature_failure_rl import check_and_record_signature_failure
from services.auth.device_signature_normalization import (
    normalize_signature_path,
    resolve_body_sha256_for_sensitive_signature,
)
from services.auth.device_signature_nonce_service import consume_device_signature_nonce
from services.auth.refresh_session import LEGACY_UNKNOWN_DEVICE, normalize_device_id, perform_revoke_all

logger = logging.getLogger("arquantix.auth.sensitive_sig")


async def require_sensitive_device_signature(
    request: Request,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    x_content_sha256: Optional[str] = Header(None, alias="X-Content-SHA256"),
) -> AdminUser:
    """
    Si ``DEVICE_SECURITY_LEVEL>=2`` : exige credential actif + en-têtes signature/nonce/Timestamp
    + ``X-Content-SHA256`` cohérent avec le corps (octets bruts ou JSON canonique si ``application/json``).

    Sinon : no-op (rétrocompat), retourne l'utilisateur courant.
    """
    if not sensitive_routes_device_signature_enabled():
        return current_user

    did = normalize_device_id(x_device_id)
    if did == LEGACY_UNKNOWN_DEVICE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-ID required for signed action",
        )

    raw_body = await request.body()
    ct = request.headers.get("content-type")
    body_hex = resolve_body_sha256_for_sensitive_signature(
        raw_body=raw_body,
        content_type=ct,
        header_sha256_hex=(x_content_sha256 or ""),
    )
    cred = (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == current_user.id,
            AuthDeviceCredential.device_id == did,
            AuthDeviceCredential.revoked_at.is_(None),
        )
        .first()
    )
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "device_credential_required", "message": "Register device key first."},
        )

    nonce = request.headers.get("X-Device-Signature-Nonce")
    sig = request.headers.get("X-Device-Signature")
    ts_raw = request.headers.get("X-Device-Signature-Timestamp")
    rl_key = f"{current_user.id}:{did}"

    try:
        ts = int(str(ts_raw).strip()) if ts_raw else 0
    except ValueError:
        check_and_record_signature_failure(rl_key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature timestamp")

    path = normalize_signature_path(request.url.path)
    method = request.method

    ok = verify_sensitive_device_signature(
        public_key_spki_b64=cred.public_key_spki_b64,
        nonce=str(nonce or ""),
        unix_ts=ts,
        method=method,
        path=path,
        body_sha256_hex=body_hex,
        signature_b64=sig,
    )
    if not ok:
        check_and_record_signature_failure(rl_key)
        logger.info("sensitive_signature_verify_failed user=%s device=%s", current_user.id, did[:8])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "device_signature_invalid"},
        )

    scoped = nonce_route_scoping_enabled()
    route_for_nonce = path if scoped else None
    if not consume_device_signature_nonce(
        db=db,
        user_id=current_user.id,
        device_id=did,
        nonce=str(nonce or ""),
        purpose="sensitive",
        route_path=route_for_nonce,
        route_scope_required=scoped,
    ):
        check_and_record_signature_failure(rl_key)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "device_signature_nonce_invalid"},
        )

    if device_risk_checks_enabled():
        score, step_up, session_revoke = evaluate_sensitive_route_risk(
            db,
            user_id=current_user.id,
            device_id=did,
            request=request,
        )
        if session_revoke:
            perform_revoke_all(db=db, request=request, user=current_user)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "device_risk_sessions_revoked",
                    "message": "Risk threshold exceeded; all sessions revoked. Sign in again.",
                    "risk_score": score,
                    "otp_login_path": "/auth/login/email-otp/start",
                },
            )
        if step_up:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "device_risk_step_up",
                    "step_up": True,
                    "risk_score": score,
                    "message": "Risk threshold exceeded; step-up authentication required.",
                    "otp_login_path": "/auth/login/email-otp/start",
                },
            )

    if sensitive_routes_device_signature_enabled():
        record_sensitive_action(current_user.id, did)

    return current_user


# TTL exposé pour l’endpoint nonce (évite import circulaire côté routes)
def default_nonce_ttl_sec() -> int:
    return device_signature_nonce_ttl_sec()
