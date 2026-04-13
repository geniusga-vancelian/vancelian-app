"""Dev/test SMS provider: simulates successful OTP send without network calls."""
from __future__ import annotations

import json
import logging
from typing import ClassVar, Optional

from services.security.masking import mask_phone_e164
from services.security.two_factor_env import is_production_like_env

from .sms_provider import SmsProvider

logger = logging.getLogger(__name__)


class FakeSmsProvider(SmsProvider):
    """Simulates SMS delivery. Must only be selected when env is not production-like."""

    audit_provider_key: ClassVar[str] = "fake_sms"

    def send_otp(self, to_e164: str, code: str, *, challenge_id: Optional[str] = None) -> None:
        if is_production_like_env():
            raise RuntimeError(
                "FakeSmsProvider cannot run in production-like environments (APP_ENV / ARQUANTIX_ENV)"
            )
        masked = mask_phone_e164(to_e164) or "****"
        payload = {
            "event": "fake_sms_otp_simulated",
            "target_masked": masked,
            "challenge_id": challenge_id,
            "code": code,
        }
        logger.info("fake_sms_provider %s", json.dumps(payload, sort_keys=True))
