"""Core 2FA logic: OTP generation, TOTP, rate limits, verification."""
from __future__ import annotations

import logging
import uuid as uuid_mod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

import pyotp
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database import Person, TwoFactorChallenge
from services.security.crypto import decrypt_totp_secret, encrypt_totp_secret
from services.security.masking import mask_email, mask_phone_e164
from services.security.providers import EmailProvider, SmsProvider
from services.security.two_factor_audit import audit_two_factor_event
from services.security.two_factor_challenge_state import enforce_challenge_verifiable
from services.security.sms_otp_core import (
    SMS_CODE_TTL_MINUTES,
    SMS_MAX_VERIFY_ATTEMPTS,
    SMS_OTP_LENGTH,
    hash_sms_otp,
    new_plaintext_sms_otp,
    verify_sms_otp,
)
from services.security.two_factor_exceptions import TwoFactorException
from services.security.two_factor_purposes import validate_purpose
from services.security.two_factor_rate_limits import (
    RESEND_SECONDS,
    check_start_rate_limits,
    check_verify_rate_limits,
)
from services.security.two_factor_target_policy import assert_target_allowed_for_person

logger = logging.getLogger(__name__)

MAX_VERIFY_ATTEMPTS = SMS_MAX_VERIFY_ATTEMPTS
CODE_TTL_MINUTES = SMS_CODE_TTL_MINUTES
OTP_LENGTH = SMS_OTP_LENGTH
TOTP_VALID_WINDOW = 1

HASH_TOTP_VERIFY = "$TOTP$"
HASH_TOTP_ENROLL = "$TOTP_ENROLL$"

CHANNEL_SMS = "sms"
CHANNEL_EMAIL = "email"
CHANNEL_TOTP = "totp"

PURPOSE_TOTP_SETUP = "totp_setup"


@dataclass
class TwoFactorRequestContext:
    relaxed: bool
    client_ip: Optional[str] = None


class TwoFactorService:
    def __init__(self, sms: SmsProvider, email: EmailProvider):
        self._sms = sms
        self._email = email

    def _otp_plaintext_for_sms_email(self) -> str:
        return new_plaintext_sms_otp()

    def _hash_otp(self, code: str) -> str:
        return hash_sms_otp(code)

    def _verify_otp_hash(self, code: str, hashed: str) -> bool:
        return verify_sms_otp(code, hashed)

    def create_challenge(
        self,
        db: Session,
        person_id: UUID,
        channel: str,
        purpose: str,
        target: Optional[str],
        ctx: TwoFactorRequestContext,
    ) -> Tuple[TwoFactorChallenge, Dict[str, Any]]:
        validate_purpose(purpose, relaxed=ctx.relaxed)
        check_start_rate_limits(
            db,
            person_id=person_id,
            channel=channel,
            purpose=purpose,
            target=target,
            source_ip=ctx.client_ip,
            relaxed=ctx.relaxed,
        )

        person = db.query(Person).filter(Person.id == person_id).first()
        if person is None:
            raise TwoFactorException("person_not_found", "Person not found")

        assert_target_allowed_for_person(
            db,
            person,
            channel=channel,
            target=target,
            purpose=purpose,
            relaxed=ctx.relaxed,
        )

        if channel in (CHANNEL_SMS, CHANNEL_EMAIL) and not ctx.relaxed:
            prov = self._sms if channel == CHANNEL_SMS else self._email
            if getattr(prov, "is_noop", True):
                raise TwoFactorException(
                    "channel_not_available",
                    "This verification channel is not available",
                )

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=CODE_TTL_MINUTES)
        meta: Dict[str, Any] = {}
        ch: TwoFactorChallenge

        if channel == CHANNEL_SMS:
            if not target:
                raise TwoFactorException("target_required", "target (E.164 phone) required for sms")
            code = self._otp_plaintext_for_sms_email()
            code_hash = self._hash_otp(code)
            ch = TwoFactorChallenge(
                id=uuid_mod.uuid4(),
                person_id=person_id,
                channel=channel,
                target=target.strip(),
                code_hash=code_hash,
                expires_at=expires,
                attempts=0,
                status="pending",
                purpose=purpose,
                source_ip=ctx.client_ip,
            )
            db.add(ch)
            db.flush()
            meta["plain_code_for_send"] = code
            meta["masked_target"] = mask_phone_e164(target)
        elif channel == CHANNEL_EMAIL:
            if not target:
                raise TwoFactorException("target_required", "target (email) required for email")
            code = self._otp_plaintext_for_sms_email()
            code_hash = self._hash_otp(code)
            tnorm = target.strip().lower()
            ch = TwoFactorChallenge(
                id=uuid_mod.uuid4(),
                person_id=person_id,
                channel=channel,
                target=tnorm,
                code_hash=code_hash,
                expires_at=expires,
                attempts=0,
                status="pending",
                purpose=purpose,
                source_ip=ctx.client_ip,
            )
            db.add(ch)
            db.flush()
            meta["plain_code_for_send"] = code
            meta["masked_target"] = mask_email(target)
        elif channel == CHANNEL_TOTP:
            if purpose == PURPOSE_TOTP_SETUP:
                secret = pyotp.random_base32()
                enc = encrypt_totp_secret(secret)
                if enc is None:
                    raise TwoFactorException(
                        "totp_encrypt_unconfigured",
                        "TWO_FACTOR_TOTP_MASTER_KEY or JWT_SECRET_KEY required to store TOTP secret",
                    )
                pj = dict(person.profile_json) if person.profile_json else {}
                sec = dict(pj.get("security") or {})
                sec["totp_pending_cipher"] = enc
                pj["security"] = sec
                person.profile_json = pj
                flag_modified(person, "profile_json")
                ch = TwoFactorChallenge(
                    id=uuid_mod.uuid4(),
                    person_id=person_id,
                    channel=channel,
                    target=None,
                    code_hash=HASH_TOTP_ENROLL,
                    expires_at=expires,
                    attempts=0,
                    status="pending",
                    purpose=purpose,
                    source_ip=ctx.client_ip,
                )
                db.add(ch)
                db.flush()
                issuer = "Arquantix"
                label = str(person_id)
                meta["otpauth_url"] = pyotp.totp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)
                meta["masked_target"] = "Authenticator app"
            else:
                active = self._get_active_totp_secret(person)
                if not active:
                    raise TwoFactorException("totp_not_configured", "TOTP is not enrolled for this person")
                ch = TwoFactorChallenge(
                    id=uuid_mod.uuid4(),
                    person_id=person_id,
                    channel=channel,
                    target=None,
                    code_hash=HASH_TOTP_VERIFY,
                    expires_at=expires,
                    attempts=0,
                    status="pending",
                    purpose=purpose,
                    source_ip=ctx.client_ip,
                )
                db.add(ch)
                db.flush()
                meta["masked_target"] = "Authenticator app"
        else:
            raise TwoFactorException("invalid_channel", "channel must be sms, email, or totp")

        audit_two_factor_event(
            db,
            person_id=person_id,
            event_type="two_factor.challenge.created",
            payload={
                "challenge_id": str(ch.id),
                "channel": channel,
                "purpose": purpose,
                "masked_target": meta.get("masked_target"),
            },
        )
        db.flush()
        return ch, meta

    def _get_active_totp_secret(self, person: Person) -> Optional[str]:
        pj = person.profile_json or {}
        sec = pj.get("security") or {}
        if not isinstance(sec, dict):
            return None
        tok = sec.get("totp_secret_cipher")
        if not tok:
            return None
        return decrypt_totp_secret(str(tok))

    def send_code(self, db: Session, challenge: TwoFactorChallenge, meta: Dict[str, Any]) -> None:
        if challenge.channel == CHANNEL_SMS:
            code = meta.get("plain_code_for_send")
            if not code or not challenge.target:
                return
            try:
                self._sms.send_otp(challenge.target, code, challenge_id=str(challenge.id))
            except Exception as exc:
                logger.warning(
                    "2fa sms send failed challenge_id=%s",
                    challenge.id,
                    exc_info=True,
                )
                audit_two_factor_event(
                    None,
                    person_id=challenge.person_id,
                    event_type="two_factor.challenge.send_failed",
                    payload={
                        "challenge_id": str(challenge.id),
                        "channel": "sms",
                        "provider": self._sms.audit_provider_key,
                    },
                    standalone=True,
                )
                raise TwoFactorException("provider_unavailable", "Could not send SMS") from exc
            logger.info("2fa sms dispatched challenge_id=%s", challenge.id)
            audit_two_factor_event(
                db,
                person_id=challenge.person_id,
                event_type="two_factor.challenge.sent",
                payload={
                    "challenge_id": str(challenge.id),
                    "channel": "sms",
                    "provider": self._sms.audit_provider_key,
                },
            )
        elif challenge.channel == CHANNEL_EMAIL:
            code = meta.get("plain_code_for_send")
            if not code or not challenge.target:
                return
            try:
                self._email.send_otp(challenge.target, code)
            except Exception as exc:
                logger.warning(
                    "2fa email send failed challenge_id=%s",
                    challenge.id,
                    exc_info=True,
                )
                audit_two_factor_event(
                    None,
                    person_id=challenge.person_id,
                    event_type="two_factor.challenge.send_failed",
                    payload={
                        "challenge_id": str(challenge.id),
                        "channel": "email",
                        "provider": "ses",
                    },
                    standalone=True,
                )
                raise TwoFactorException("provider_unavailable", "Could not send email") from exc
            logger.info("2fa email dispatched challenge_id=%s", challenge.id)
            audit_two_factor_event(
                db,
                person_id=challenge.person_id,
                event_type="two_factor.challenge.sent",
                payload={"challenge_id": str(challenge.id), "channel": "email", "provider": "ses"},
            )
        else:
            logger.info("2fa totp challenge created challenge_id=%s (no outbound send)", challenge.id)

    def verify_code(
        self,
        db: Session,
        challenge_id: UUID,
        code: str,
        person_id: UUID,
        ctx: TwoFactorRequestContext,
    ) -> None:
        check_verify_rate_limits(db, person_id=person_id, relaxed=ctx.relaxed)
        ch = (
            db.query(TwoFactorChallenge)
            .filter(TwoFactorChallenge.id == challenge_id, TwoFactorChallenge.person_id == person_id)
            .first()
        )
        if ch is None:
            raise TwoFactorException("challenge_not_found", "Challenge not found")

        enforce_challenge_verifiable(db, ch)

        if ch.attempts >= MAX_VERIFY_ATTEMPTS:
            ch.status = "failed"
            db.flush()
            raise TwoFactorException("too_many_attempts", "Too many attempts")

        ok = False
        person = db.query(Person).filter(Person.id == person_id).first()
        if person is None:
            raise TwoFactorException("person_not_found", "Person not found")

        if ch.channel in (CHANNEL_SMS, CHANNEL_EMAIL):
            ok = self._verify_otp_hash(code.strip(), ch.code_hash)
        elif ch.channel == CHANNEL_TOTP:
            if ch.code_hash == HASH_TOTP_ENROLL:
                ok = self._verify_totp_enrollment(db, person, code.strip())
            else:
                secret = self._get_active_totp_secret(person)
                if secret:
                    ok = bool(pyotp.TOTP(secret).verify(code.strip(), valid_window=TOTP_VALID_WINDOW))
        else:
            ok = False

        if not ok:
            ch.attempts += 1
            if ch.attempts >= MAX_VERIFY_ATTEMPTS:
                ch.status = "failed"
            db.flush()
            audit_two_factor_event(
                db,
                person_id=person_id,
                event_type="two_factor.challenge.verify_failed",
                payload={
                    "challenge_id": str(ch.id),
                    "channel": ch.channel,
                    "purpose": ch.purpose,
                    "attempts": ch.attempts,
                },
            )
            db.flush()
            raise TwoFactorException("invalid_code", "Invalid code")

        ch.status = "verified"
        db.flush()
        audit_two_factor_event(
            db,
            person_id=person_id,
            event_type="two_factor.challenge.verify_succeeded",
            payload={
                "challenge_id": str(ch.id),
                "channel": ch.channel,
                "purpose": ch.purpose,
            },
        )
        db.flush()
        logger.info("2fa verified challenge_id=%s channel=%s purpose=%s", ch.id, ch.channel, ch.purpose)

    def _verify_totp_enrollment(self, db: Session, person: Person, code: str) -> bool:
        pj = dict(person.profile_json) if person.profile_json else {}
        sec = dict(pj.get("security") or {})
        pending = sec.get("totp_pending_cipher")
        if not pending:
            return False
        secret = decrypt_totp_secret(str(pending))
        if not secret:
            return False
        if not pyotp.TOTP(secret).verify(code, valid_window=TOTP_VALID_WINDOW):
            return False
        enc_active = encrypt_totp_secret(secret)
        if enc_active is None:
            return False
        sec["totp_secret_cipher"] = enc_active
        sec.pop("totp_pending_cipher", None)
        pj["security"] = sec
        person.profile_json = pj
        flag_modified(person, "profile_json")
        db.flush()
        audit_two_factor_event(
            db,
            person_id=person.id,
            event_type="two_factor.challenge.totp_activated",
            payload={},
        )
        db.flush()
        return True


def supersede_pending_sms_challenges_for_target(
    db: Session,
    *,
    person_id: UUID,
    purpose: str,
    target_e164: str,
) -> int:
    """Mark pending SMS challenges for the same person/purpose/target as superseded.

    Used by registration interaction resend so only one active OTP exists; verify rejects
    superseded challenges via enforce_challenge_verifiable.
    """
    tnorm = target_e164.strip()
    rows = (
        db.query(TwoFactorChallenge)
        .filter(
            TwoFactorChallenge.person_id == person_id,
            TwoFactorChallenge.channel == CHANNEL_SMS,
            TwoFactorChallenge.purpose == purpose,
            TwoFactorChallenge.target == tnorm,
            TwoFactorChallenge.status == "pending",
        )
        .all()
    )
    n = 0
    for ch in rows:
        ch.status = "superseded"
        n += 1
        audit_two_factor_event(
            db,
            person_id=person_id,
            event_type="two_factor.challenge.superseded",
            payload={
                "challenge_id": str(ch.id),
                "channel": "sms",
                "purpose": purpose,
                "reason": "registration_resend",
            },
        )
    if n:
        db.flush()
    return n


def latest_sms_challenge_for_target(
    db: Session,
    *,
    person_id: UUID,
    purpose: str,
    target_e164: str,
) -> Optional[TwoFactorChallenge]:
    tnorm = target_e164.strip()
    return (
        db.query(TwoFactorChallenge)
        .filter(
            TwoFactorChallenge.person_id == person_id,
            TwoFactorChallenge.channel == CHANNEL_SMS,
            TwoFactorChallenge.purpose == purpose,
            TwoFactorChallenge.target == tnorm,
        )
        .order_by(desc(TwoFactorChallenge.created_at))
        .first()
    )


def get_two_factor_service() -> TwoFactorService:
    from services.security.providers import get_email_provider, get_sms_provider

    return TwoFactorService(get_sms_provider(), get_email_provider())
