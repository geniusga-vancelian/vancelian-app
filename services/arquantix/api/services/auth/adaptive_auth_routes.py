"""Endpoint pré-décision Adaptive Auth (orchestrateur central)."""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from schemas import AdaptiveAuthDecisionPayload, AdaptiveAuthOrchestrateRequest
from services.auth.adaptive_auth_orchestrator import (
    AdaptiveAuthDecision,
    is_adaptive_auth_enabled,
    orchestrate_login_strategy_from_request,
    persist_adaptive_auth_decision,
)
from services.auth.refresh_session import normalize_device_id

router = APIRouter(prefix="/auth", tags=["auth-adaptive"])


def _normalize_phone_e164(raw: str) -> str:
    t = re.sub(r"\s+", "", (raw or "").strip())
    if not t.startswith("+"):
        t = "+" + t.lstrip("+")
    return t


@router.post("/login/orchestrate", response_model=AdaptiveAuthDecisionPayload)
def login_orchestrate(
    request: Request,
    body: AdaptiveAuthOrchestrateRequest,
    db: Session = Depends(get_db),
):
    """
    Pré-décision : même logique que les flux start sans envoyer OTP/SMS.
    Utilisateur inconnu → réponse générique (anti-énumération).
    """
    if not is_adaptive_auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "adaptive_auth_disabled", "message": "Adaptive auth disabled."},
        )

    user: Optional[AdminUser] = None
    ident: dict
    channel = "orchestrate"
    if body.identifier_type == "email":
        em = str(body.identifier).strip().lower()
        user = db.query(AdminUser).filter(AdminUser.email == em).first()
        ident = {"kind": "email", "value": em}
    else:
        phone = _normalize_phone_e164(body.identifier)
        user = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
        ident = {"kind": "phone_e164", "value": phone}

    if user is None:
        neutral = AdaptiveAuthDecision(
            primary_method="otp_sms" if body.identifier_type == "phone_e164" else "otp_email",
            fallback_methods=["password"],
            reason_codes=["unknown_identifier_benign"],
            blocked=False,
            ui_variant="standard",
        )
        return AdaptiveAuthDecisionPayload(**neutral.to_dict())

    decision, _ = orchestrate_login_strategy_from_request(
        db,
        request,
        user,
        device_header=request.headers.get("x-device-id"),
        login_identifier=ident,
        login_channel=channel,
        attestation_trusted=False,
    )
    persist_adaptive_auth_decision(
        db,
        user_id=user.id,
        device_id=normalize_device_id(request.headers.get("x-device-id")),
        decision=decision,
        login_channel=channel,
    )
    db.commit()
    return AdaptiveAuthDecisionPayload(**decision.to_dict())
