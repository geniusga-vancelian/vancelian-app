"""HTTP API for reusable 2FA (SMS / email OTP + TOTP)."""
from __future__ import annotations

import logging
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.security.deps import _bearer, resolve_person_id
from services.security.two_factor_env import (
    is_two_factor_relaxed,
    two_factor_dev_code_for_api_exposure,
)
from services.security.two_factor_errors import http_detail_for_code
from services.security.two_factor_service import (
    RESEND_SECONDS,
    TwoFactorException,
    TwoFactorRequestContext,
    get_two_factor_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/2fa", tags=["Two-Factor Authentication"])

_START_RATE_LIMIT_CODES = frozenset(
    {
        "resend_rate_limited",
        "start_quota_exceeded",
        "target_rate_limited",
        "ip_rate_limited",
    }
)


def _raise_2fa_http(exc: TwoFactorException) -> None:
    logger.warning("2fa rejected internal_code=%s", exc.code)
    status_code, ext_code, msg = http_detail_for_code(exc.code, exc.message)
    raise HTTPException(status_code, detail={"code": ext_code, "message": msg})


class TwoFactorStartRequest(BaseModel):
    channel: Literal["sms", "email", "totp"]
    purpose: str = Field(..., min_length=1, max_length=64)
    target: Optional[str] = Field(None, description="E.164 phone or email when channel is sms/email")
    person_id: Optional[UUID] = Field(
        None,
        description="Only when TWO_FACTOR_REQUIRE_AUTH=false (dev/tests)",
    )


class TwoFactorStartResponse(BaseModel):
    challenge_id: str
    expires_at: str
    masked_target: Optional[str]
    channel: str
    purpose: str
    resend_after_seconds: int = RESEND_SECONDS
    otpauth_url: Optional[str] = None
    dev_code: Optional[str] = Field(
        None,
        description="Dev/test only: echoed OTP when TWO_FACTOR_DEV_EXPOSE_CODE is enabled",
    )


class TwoFactorVerifyRequest(BaseModel):
    challenge_id: UUID
    code: str = Field(..., min_length=6, max_length=12)
    person_id: Optional[UUID] = Field(None, description="Dev only when TWO_FACTOR_REQUIRE_AUTH=false")


class TwoFactorVerifyResponse(BaseModel):
    success: bool
    status: str


@router.post(
    "/start",
    response_model=TwoFactorStartResponse,
    response_model_exclude_none=True,
)
def two_factor_start(
    request: Request,
    body: TwoFactorStartRequest,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    ctx = TwoFactorRequestContext(
        relaxed=is_two_factor_relaxed(app_testing=getattr(request.app.state, "testing", False)),
        client_ip=(request.client.host if request.client else None),
    )
    svc = get_two_factor_service()
    try:
        person_id = resolve_person_id(
            body.person_id,
            credentials,
            db,
            anti_enum_missing_person=True,
        )
        ch, meta = svc.create_challenge(
            db,
            person_id,
            body.channel,
            body.purpose,
            body.target,
            ctx,
        )
        svc.send_code(db, ch, meta)
        db.commit()
    except TwoFactorException as e:
        if e.code in _START_RATE_LIMIT_CODES:
            try:
                db.commit()
            except Exception:
                db.rollback()
        else:
            db.rollback()
        _raise_2fa_http(e)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    dev_code = None
    if body.channel in ("sms", "email"):
        dev_code = two_factor_dev_code_for_api_exposure()
    return TwoFactorStartResponse(
        challenge_id=str(ch.id),
        expires_at=ch.expires_at.isoformat(),
        masked_target=meta.get("masked_target"),
        channel=ch.channel,
        purpose=ch.purpose,
        otpauth_url=meta.get("otpauth_url"),
        dev_code=dev_code,
    )


@router.post("/verify", response_model=TwoFactorVerifyResponse)
def two_factor_verify(
    request: Request,
    body: TwoFactorVerifyRequest,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    ctx = TwoFactorRequestContext(
        relaxed=is_two_factor_relaxed(app_testing=getattr(request.app.state, "testing", False)),
        client_ip=(request.client.host if request.client else None),
    )
    svc = get_two_factor_service()
    try:
        person_id = resolve_person_id(
            body.person_id,
            credentials,
            db,
            anti_enum_missing_person=True,
        )
        svc.verify_code(db, body.challenge_id, body.code, person_id, ctx)
        db.commit()
    except TwoFactorException as e:
        db.commit()
        _raise_2fa_http(e)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return TwoFactorVerifyResponse(success=True, status="verified")
