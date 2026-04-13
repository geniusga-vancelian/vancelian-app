"""PR E — FastAPI Depends : enforcement attestation sur routes sensibles."""
from __future__ import annotations

import logging
import uuid as uuid_lib
from typing import Any, Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY, get_current_user, oauth2_scheme
from database import AdminUser, AuthDeviceCredential, AuthSession, get_db
from services.auth.device_attestation_pr_e_policy import (
    device_attestation_required_sensitive,
    device_trust_required_level,
)
from services.auth.device_attestation_service import evaluate_header_for_auth
from services.auth.device_attestation_trust import (
    TRUST_TIER_LOW,
    compute_attestation_trust_level,
    tier_rank,
)
from services.auth.refresh_session import LEGACY_UNKNOWN_DEVICE, normalize_device_id

logger = logging.getLogger("arquantix.auth.device_attestation_pr_e")

LOG_EVENT_REQUIRED = "device_attestation_required"
LOG_EVENT_TRUST_INSUFFICIENT = "device_trust_level_insufficient"


def _resolve_session_from_access_token(db: Session, token: str) -> Optional[AuthSession]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    sid = payload.get("sid")
    if not sid:
        return None
    try:
        suid = uuid_lib.UUID(str(sid))
    except (ValueError, TypeError):
        return None
    return (
        db.query(AuthSession)
        .filter(
            AuthSession.id == suid,
            AuthSession.revoked_at.is_(None),
        )
        .first()
    )


def _credential_bound(db: Session, *, user_id: int, device_id: str) -> bool:
    row = (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == user_id,
            AuthDeviceCredential.device_id == device_id,
            AuthDeviceCredential.revoked_at.is_(None),
            AuthDeviceCredential.attestation_bound_at.isnot(None),
        )
        .first()
    )
    return row is not None


def evaluate_effective_attestation_tier(
    *,
    db: Session,
    request: Request,
    user_id: int,
    device_id: str,
    token: str,
    attestation_header_raw: Optional[str],
) -> tuple[str, Optional[Any]]:
    """
    Combine session (``sid`` dans le JWT) et/ou en-tête ``X-Device-Attestation`` frais.
    L’en-tête prime pour refléter une attestation renouvelée.
    """
    _ = request
    session = _resolve_session_from_access_token(db, token)
    att_res: Optional[Any] = None
    if attestation_header_raw and str(attestation_header_raw).strip():
        att_res, _trust, _step = evaluate_header_for_auth(
            db=db,
            request_device_id=device_id,
            attestation_header_raw=attestation_header_raw,
            legacy_unknown_label=LEGACY_UNKNOWN_DEVICE,
        )
        if att_res is not None:
            tier = compute_attestation_trust_level(
                attestation_verified_at=None,
                attestation_type=att_res.attestation_type,
                attestation_metadata=att_res.metadata,
                credential_has_attestation_bound=_credential_bound(db, user_id=user_id, device_id=device_id),
                attestation_result=att_res,
            )
            return tier, att_res

    if session is None:
        return (
            compute_attestation_trust_level(
                attestation_verified_at=None,
                attestation_type=None,
                attestation_metadata=None,
                credential_has_attestation_bound=_credential_bound(db, user_id=user_id, device_id=device_id),
                attestation_result=None,
            ),
            None,
        )

    return (
        compute_attestation_trust_level(
            attestation_verified_at=session.attestation_verified_at,
            attestation_type=session.attestation_type,
            attestation_metadata=dict(session.attestation_metadata or {}),
            credential_has_attestation_bound=_credential_bound(db, user_id=user_id, device_id=device_id),
            attestation_result=None,
        ),
        None,
    )


def require_device_attestation(required_level: Optional[str] = None) -> Callable:
    """
    À combiner avec ``get_current_user`` (Bearer). Si politique désactivée → no-op.

    - Sans attestation exploitable → 403 ``device_attestation_required``
    - Si tier < requis → 403 ``device_trust_level_insufficient``
    """
    req = required_level or device_trust_required_level()

    async def _dep(
        request: Request,
        db: Session = Depends(get_db),
        current_user: AdminUser = Depends(get_current_user),
        token: str = Depends(oauth2_scheme),
        x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
        x_device_attestation: Optional[str] = Header(None, alias="X-Device-Attestation"),
    ) -> None:
        if not device_attestation_required_sensitive():
            return
        did = normalize_device_id(x_device_id)
        if did == LEGACY_UNKNOWN_DEVICE:
            logger.info(
                LOG_EVENT_REQUIRED,
                extra={
                    "event": LOG_EVENT_REQUIRED,
                    "reason": "missing_device_id",
                    "user_id": current_user.id,
                    "route": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "device_attestation_required",
                    "message": "X-Device-ID and attestation context required for this action.",
                },
            )

        tier, _ = evaluate_effective_attestation_tier(
            db=db,
            request=request,
            user_id=current_user.id,
            device_id=did,
            token=token,
            attestation_header_raw=x_device_attestation,
        )
        need = tier_rank(req)
        got = tier_rank(tier)
        if tier == TRUST_TIER_LOW:
            logger.info(
                LOG_EVENT_REQUIRED,
                extra={
                    "event": LOG_EVENT_REQUIRED,
                    "reason": "tier_low",
                    "user_id": current_user.id,
                    "route": request.url.path,
                    "device_prefix": did[:12],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "device_attestation_required",
                    "message": "Valid device attestation required for this action.",
                    "attestation_trust_tier": tier,
                },
            )
        if got < need:
            logger.info(
                LOG_EVENT_TRUST_INSUFFICIENT,
                extra={
                    "event": LOG_EVENT_TRUST_INSUFFICIENT,
                    "user_id": current_user.id,
                    "route": request.url.path,
                    "required_tier": req,
                    "current_tier": tier,
                    "device_prefix": did[:12],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "device_trust_level_insufficient",
                    "message": f"Attestation trust {tier} is below required {req}.",
                    "required_tier": req,
                    "current_tier": tier,
                },
            )

    return _dep


def require_device_attestation_mobile(required_level: Optional[str] = None) -> Callable:
    """Même politique pour routes résolues via JWT app (PeClient) — utilise ``sub`` / ``sid``."""
    req = required_level or device_trust_required_level()

    async def _dep(
        request: Request,
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme),
        x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
        x_device_attestation: Optional[str] = Header(None, alias="X-Device-Attestation"),
    ) -> None:
        if not device_attestation_required_sensitive():
            return
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        sub = str(payload.get("sub") or "")
        if not sub.startswith("au:"):
            return
        try:
            user_id = int(sub.split(":", 1)[1])
        except (ValueError, IndexError):
            return
        did = normalize_device_id(x_device_id)
        if did == LEGACY_UNKNOWN_DEVICE:
            logger.info(
                LOG_EVENT_REQUIRED,
                extra={"event": LOG_EVENT_REQUIRED, "reason": "missing_device_id", "user_id": user_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "device_attestation_required", "message": "X-Device-ID required."},
            )
        tier, _ = evaluate_effective_attestation_tier(
            db=db,
            request=request,
            user_id=user_id,
            device_id=did,
            token=token,
            attestation_header_raw=x_device_attestation,
        )
        need = tier_rank(req)
        got = tier_rank(tier)
        if tier == TRUST_TIER_LOW:
            logger.info(
                LOG_EVENT_REQUIRED,
                extra={"event": LOG_EVENT_REQUIRED, "user_id": user_id, "route": request.url.path},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "device_attestation_required", "current_tier": tier},
            )
        if got < need:
            logger.info(
                LOG_EVENT_TRUST_INSUFFICIENT,
                extra={
                    "event": LOG_EVENT_TRUST_INSUFFICIENT,
                    "user_id": user_id,
                    "required_tier": req,
                    "current_tier": tier,
                    "route": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "device_trust_level_insufficient",
                    "required_tier": req,
                    "current_tier": tier,
                },
            )

    return _dep
