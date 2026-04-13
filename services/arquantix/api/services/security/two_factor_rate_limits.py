"""Multi-dimensional rate limits for 2FA start/verify."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import AuditEvent, TwoFactorChallenge
from services.security.two_factor_audit import audit_two_factor_event
from services.security.two_factor_exceptions import TwoFactorException

RESEND_SECONDS = 30
START_LONG_WINDOW_MINUTES = 15
START_MAX_PER_PERSON_SMS_EMAIL = 5
START_MAX_PER_TARGET = 10
START_MAX_PER_IP = 25
VERIFY_FAIL_WINDOW_MINUTES = 10
VERIFY_FAIL_MAX_PER_PERSON = 25


def _now() -> datetime:
    return datetime.now(timezone.utc)


def check_start_rate_limits(
    db: Session,
    *,
    person_id: UUID,
    channel: str,
    purpose: str,
    target: Optional[str],
    source_ip: Optional[str],
    relaxed: bool,
) -> None:
    """Short window per person/channel/purpose + optional long-window & target/IP buckets."""
    since_short = _now() - timedelta(seconds=RESEND_SECONDS)
    # Only *pending* challenges count for the short cooldown so registration resend can
    # supersede the current OTP and immediately create a replacement without a false block
    # from the just-superseded row (still in the time window but no longer pending).
    last = (
        db.query(TwoFactorChallenge)
        .filter(
            TwoFactorChallenge.person_id == person_id,
            TwoFactorChallenge.channel == channel,
            TwoFactorChallenge.purpose == purpose,
            TwoFactorChallenge.created_at >= since_short,
            TwoFactorChallenge.status == "pending",
        )
        .order_by(TwoFactorChallenge.created_at.desc())
        .first()
    )
    if last is not None:
        audit_two_factor_event(
            db,
            person_id=person_id,
            event_type="two_factor.challenge.resend_blocked",
            payload={
                "channel": channel,
                "purpose": purpose,
                "reason": "short_window",
            },
        )
        raise TwoFactorException(
            "resend_rate_limited",
            f"Wait {RESEND_SECONDS}s before requesting a new code",
        )

    if relaxed:
        return

    since_long = _now() - timedelta(minutes=START_LONG_WINDOW_MINUTES)
    long_count = (
        db.query(func.count(TwoFactorChallenge.id))
        .filter(
            TwoFactorChallenge.person_id == person_id,
            TwoFactorChallenge.channel.in_(("sms", "email")),
            TwoFactorChallenge.created_at >= since_long,
        )
        .scalar()
    )
    if (long_count or 0) >= START_MAX_PER_PERSON_SMS_EMAIL:
        audit_two_factor_event(
            db,
            person_id=person_id,
            event_type="two_factor.challenge.rate_limited",
            payload={"channel": channel, "purpose": purpose, "reason": "person_quota"},
        )
        raise TwoFactorException(
            "start_quota_exceeded",
            "Too many verification requests in a short period",
        )

    if target and channel in ("sms", "email"):
        tnorm = target.strip().lower() if channel == "email" else target.strip()
        tgt_count = (
            db.query(func.count(TwoFactorChallenge.id))
            .filter(
                TwoFactorChallenge.channel == channel,
                TwoFactorChallenge.created_at >= since_long,
                TwoFactorChallenge.target == tnorm,
            )
            .scalar()
        )
        if (tgt_count or 0) >= START_MAX_PER_TARGET:
            audit_two_factor_event(
                db,
                person_id=person_id,
                event_type="two_factor.challenge.rate_limited",
                payload={"channel": channel, "purpose": purpose, "reason": "target_quota"},
            )
            raise TwoFactorException(
                "target_rate_limited",
                "Too many verification requests for this destination",
            )

    if source_ip:
        ip_count = (
            db.query(func.count(TwoFactorChallenge.id))
            .filter(
                TwoFactorChallenge.created_at >= since_long,
                TwoFactorChallenge.source_ip == source_ip,
            )
            .scalar()
        )
        if (ip_count or 0) >= START_MAX_PER_IP:
            audit_two_factor_event(
                db,
                person_id=person_id,
                event_type="two_factor.challenge.rate_limited",
                payload={"channel": channel, "purpose": purpose, "reason": "ip_quota"},
            )
            raise TwoFactorException(
                "ip_rate_limited",
                "Too many verification requests from this network",
            )


def check_verify_rate_limits(db: Session, *, person_id: UUID, relaxed: bool) -> None:
    if relaxed:
        return
    since = _now() - timedelta(minutes=VERIFY_FAIL_WINDOW_MINUTES)
    n = (
        db.query(func.count(AuditEvent.id))
        .filter(
            AuditEvent.person_id == person_id,
            AuditEvent.event_type == "two_factor.challenge.verify_failed",
            AuditEvent.created_at >= since,
        )
        .scalar()
    )
    if (n or 0) >= VERIFY_FAIL_MAX_PER_PERSON:
        audit_two_factor_event(
            db,
            person_id=person_id,
            event_type="two_factor.challenge.rate_limited",
            payload={"reason": "verify_fail_quota"},
        )
        raise TwoFactorException(
            "verify_rate_limited",
            "Too many verification attempts",
        )
