"""Challenge nonce pour attestation App Attest / Play Integrity."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.auth.auth_rate_limit import build_auth_rate_limiter, client_ip_for_rl
from services.auth.device_attestation_service import is_device_attestation_enabled, mint_attestation_nonce
from services.auth.refresh_session import normalize_device_id

router = APIRouter(prefix="/auth", tags=["auth-device-attestation"])


class AttestationChallengeRequest(BaseModel):
    platform: str = Field(default="unknown", max_length=32)


class AttestationChallengeResponse(BaseModel):
    nonce: str
    expires_at: datetime


@router.post("/attestation/challenge", response_model=AttestationChallengeResponse)
def create_attestation_challenge(
    request: Request,
    body: AttestationChallengeRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    if not is_device_attestation_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device attestation is disabled (DEVICE_ATTESTATION_ENABLED)",
        )
    try:
        build_auth_rate_limiter().check_login(client_ip_for_rl(request))
    except HTTPException:
        raise
    device_id = normalize_device_id(x_device_id)
    nonce, exp = mint_attestation_nonce(db=db, platform=body.platform, device_id=device_id)
    return AttestationChallengeResponse(nonce=nonce, expires_at=exp)
