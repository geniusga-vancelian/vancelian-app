"""Interaction screens (registration) — phone SMS verification helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import Person, RegistrationSession, RegistrationStepScreen, TwoFactorChallenge
from services.security.two_factor_rate_limits import RESEND_SECONDS

from .phone_validation import USER_MESSAGES, validate_mobile_phone_basic

INTERACTION_PHONE_SMS = "phone_verification_sms"


def effective_screen_type(screen: RegistrationStepScreen) -> str:
    st = getattr(screen, "screen_type", None) or "form"
    return st if st in ("form", "interaction", "permission_prompt") else "form"


def parse_phone_verification_config(screen: RegistrationStepScreen) -> Dict[str, Any]:
    raw = screen.interaction_config_json or {}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "source_field_slug": str(raw.get("source_field_slug") or "").strip(),
        "verified_flag_slug": str(raw.get("verified_flag_slug") or "").strip(),
        "purpose": str(raw.get("purpose") or "verify_phone").strip(),
    }


def default_phone_region_from_session(session: RegistrationSession) -> str:
    """ISO alpha-2 hint for national-format numbers (maps EU/UAE product codes).

    When the jurisdiction code does not map to a default region, returns ``FR``
    as the **explicit** product fallback for SMS interaction re-validation only.
    """
    from .phone_validation import default_phone_region_iso2

    jc = ""
    if session.jurisdiction is not None:
        jc = str(getattr(session.jurisdiction, "code", "") or "").strip().upper()
    reg = default_phone_region_iso2(jc)
    return reg if reg is not None else "FR"


def ensure_session_person(db: Session, session: RegistrationSession) -> Person:
    if session.person_id:
        person = db.query(Person).filter(Person.id == session.person_id).first()
        if person:
            return person
    jurisdiction_code = session.jurisdiction.code if session.jurisdiction else None
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction=jurisdiction_code,
        profile_json={"collected": {}, "computed": {}, "compliance": {}},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    session.person_id = person.id
    db.flush()
    return person


def find_reusable_sms_challenge(
    db: Session,
    *,
    person_id: UUID,
    purpose: str,
    target_e164: str,
) -> Optional[TwoFactorChallenge]:
    now = datetime.now(timezone.utc)
    return (
        db.query(TwoFactorChallenge)
        .filter(
            TwoFactorChallenge.person_id == person_id,
            TwoFactorChallenge.channel == "sms",
            TwoFactorChallenge.purpose == purpose,
            TwoFactorChallenge.target == target_e164,
            TwoFactorChallenge.status == "pending",
            TwoFactorChallenge.expires_at > now,
        )
        .order_by(desc(TwoFactorChallenge.created_at))
        .first()
    )


def validate_phone_verification_prerequisites(
    screen: RegistrationStepScreen,
    context: Dict[str, Any],
    *,
    default_region: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Returns (phone_e164, purpose, verified_flag_slug) or raises RegistrationInteractionError."""
    cfg = parse_phone_verification_config(screen)
    src = cfg["source_field_slug"]
    flag = cfg["verified_flag_slug"]
    purpose = cfg["purpose"] or "verify_phone"
    if not src or not flag:
        raise RegistrationInteractionError(
            "interaction_misconfigured",
            "Interaction screen is missing source_field_slug or verified_flag_slug",
        )
    raw = context.get(src)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise RegistrationInteractionError(
            "phone_number_required",
            "Please enter your phone number",
        )
    res = validate_mobile_phone_basic(
        raw,
        selected_country_iso2=None,
        jurisdiction_default_region=default_region or "FR",
    )
    if not res.ok:
        raise RegistrationInteractionError(
            res.error_code or "invalid_phone_number",
            res.user_message or USER_MESSAGES["invalid_phone_number"],
        )
    return res.normalized_e164, purpose, flag


class RegistrationInteractionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def build_phone_sms_read_payload(
    db: Session,
    session: RegistrationSession,
    screen: RegistrationStepScreen,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Read-only payload for GET current screen (no SMS send, no new challenge)."""
    from services.security.masking import mask_phone_e164

    cfg = parse_phone_verification_config(screen)
    try:
        phone, purpose, vflag = validate_phone_verification_prerequisites(
            screen,
            context,
            default_region=default_phone_region_from_session(session),
        )
    except RegistrationInteractionError as e:
        return {
            "challenge_ready": False,
            "error_code": e.code,
            "message": e.message,
            "purpose": cfg.get("purpose") or "verify_phone",
            "source_field_slug": cfg.get("source_field_slug") or "",
            "verified_flag_slug": cfg.get("verified_flag_slug") or "",
            "resend_after_seconds": RESEND_SECONDS,
        }
    out: Dict[str, Any] = {
        "challenge_ready": False,
        "purpose": purpose,
        "source_field_slug": cfg["source_field_slug"],
        "verified_flag_slug": vflag,
        "resend_after_seconds": RESEND_SECONDS,
    }
    if session.person_id:
        ch = find_reusable_sms_challenge(
            db, person_id=session.person_id, purpose=purpose, target_e164=phone
        )
        if ch:
            out["challenge_ready"] = True
            out["challenge_id"] = str(ch.id)
            out["target_masked"] = mask_phone_e164(ch.target)
            out["challenge_reused_hint"] = True
    return out


def session_slug_to_compliance(slug: str) -> bool:
    """Whether a session field slug is projected under profile_json[\"compliance\"]."""
    if slug in ("phone_verified_at", "phone_verification_channel"):
        return True
    if slug == "phone_verified":
        return True
    if slug.endswith("_verified"):
        return True
    return False
