"""SMS delivery abstraction (Twilio default; swap for Vonage later)."""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import ClassVar, Optional

import httpx

from services.security.two_factor_env import is_production_like_env

logger = logging.getLogger(__name__)

_TRUTHY = frozenset({"1", "true", "yes"})


class SmsProvider(ABC):
    audit_provider_key: ClassVar[str] = "unknown_sms"

    @property
    def is_noop(self) -> bool:
        return False

    @abstractmethod
    def send_otp(self, to_e164: str, code: str, *, challenge_id: Optional[str] = None) -> None:
        """Send OTP SMS. Raises on failure."""


class NoopSmsProvider(SmsProvider):
    audit_provider_key: ClassVar[str] = "noop_sms"

    @property
    def is_noop(self) -> bool:
        return True

    def send_otp(self, to_e164: str, code: str, *, challenge_id: Optional[str] = None) -> None:
        logger.warning("SMS provider noop: would send to masked destination (code not logged)")


class TwilioSmsProvider(SmsProvider):
    """Twilio REST API (basic auth)."""

    audit_provider_key: ClassVar[str] = "twilio"

    def __init__(self) -> None:
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER", "")

    def send_otp(self, to_e164: str, code: str, *, challenge_id: Optional[str] = None) -> None:
        if not (self.account_sid and self.auth_token and self.from_number):
            raise RuntimeError("Twilio env vars missing")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        body = f"Your security code is {code}. Expires in 5 min. Ignore if not you."
        data = {"To": to_e164, "From": self.from_number, "Body": body}
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                r.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning(
                "Twilio SMS HTTP error status=%s",
                getattr(getattr(e, "response", None), "status_code", None),
            )
            raise RuntimeError("twilio_send_failed") from e


def get_sms_provider() -> SmsProvider:
    fake_requested = os.getenv("FAKE_SMS_PROVIDER", "").strip().lower() in _TRUTHY

    if is_production_like_env():
        if fake_requested:
            raise RuntimeError(
                "FAKE_SMS_PROVIDER is forbidden when APP_ENV / ARQUANTIX_ENV is "
                "production, prod, or staging"
            )
        if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
            return TwilioSmsProvider()
        return NoopSmsProvider()

    if fake_requested:
        from .fake_sms_provider import FakeSmsProvider

        return FakeSmsProvider()

    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        return TwilioSmsProvider()
    return NoopSmsProvider()
