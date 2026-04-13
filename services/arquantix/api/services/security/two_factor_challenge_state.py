"""Challenge lifecycle checks (2FA)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from services.security.two_factor_audit import audit_two_factor_event
from services.security.two_factor_exceptions import TwoFactorException

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from database import TwoFactorChallenge


def enforce_challenge_verifiable(db: "Session", ch: "TwoFactorChallenge") -> None:
    if ch.status == "superseded":
        raise TwoFactorException(
            "challenge_superseded",
            "This code was replaced. Request a new code.",
        )
    if ch.status != "pending":
        raise TwoFactorException(
            "invalid_state",
            "Challenge is no longer pending",
        )
    now = datetime.now(timezone.utc)
    if ch.expires_at <= now:
        ch.status = "expired"
        db.flush()
        audit_two_factor_event(
            db,
            person_id=ch.person_id,
            event_type="two_factor.challenge.expired",
            payload={"challenge_id": str(ch.id), "channel": ch.channel, "purpose": ch.purpose},
        )
        raise TwoFactorException("challenge_expired", "Code expired")
