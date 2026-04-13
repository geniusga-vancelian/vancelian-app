"""ACK : le client signale que le PIN local a été configuré — puis émission JWT plein accès."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import AdminUser, Person, get_db
from services.auth.device_attestation_service import DEVICE_TRUST_TRUSTED
from services.auth.refresh_session import issue_fresh_auth_session

router = APIRouter(prefix="/auth", tags=["auth-local-security"])


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class LocalPasscodeAckResponse(BaseModel):
    local_passcode_registered_at: str = Field(
        description="Horodatage serveur ISO 8601 (UTC, suffixe Z).",
    )
    already_acknowledged: bool = False
    access_token: Optional[str] = Field(
        default=None,
        description="Nouveau jeton d’accès (session pleine, sans sec_inc).",
    )
    refresh_token: Optional[str] = Field(default=None, description="Nouveau refresh token.")
    token_type: Optional[str] = Field(default=None, description="Typiquement bearer.")


@router.post(
    "/security/local-passcode-ack",
    response_model=LocalPasscodeAckResponse,
    summary="ACK configuration passcode local puis session complète",
)
def post_local_passcode_ack(
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> LocalPasscodeAckResponse:
    """Idempotent sur l’horodatage ; émet toujours une paire JWT complète (sans ``sec_inc``)."""
    if user.person_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "security.no_person_linked",
                "message": "Compte sans personne liée — ACK impossible.",
            },
        )

    person = db.query(Person).filter(Person.id == user.person_id).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "person.not_found", "message": "Personne introuvable."},
        )

    pj: Dict[str, Any] = dict(person.profile_json or {})
    sec: Dict[str, Any] = dict(pj.get("security") or {}) if isinstance(pj.get("security"), dict) else {}

    existing = sec.get("local_passcode_registered_at")
    already = bool(existing is not None and str(existing).strip())

    if not already:
        ts = _utc_iso_z()
        sec["local_passcode_registered_at"] = ts
        if x_device_id and str(x_device_id).strip():
            sec["local_passcode_ack_device_id"] = str(x_device_id).strip()[:128]
        pj["security"] = sec
        person.profile_json = pj
        db.add(person)
        db.commit()
        db.refresh(person)
        registered_at = ts
    else:
        registered_at = str(existing).strip()

    db.refresh(user)
    tokens = issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=x_device_id,
        success_event_type="auth.security.local_passcode_ack",
        success_metadata={"person_id": str(user.person_id)},
        device_trust_level=DEVICE_TRUST_TRUSTED,
        step_up_otp_required=False,
        auth_strength="otp",
    )

    return LocalPasscodeAckResponse(
        local_passcode_registered_at=registered_at,
        already_acknowledged=already,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_type=tokens.get("token_type"),
    )
