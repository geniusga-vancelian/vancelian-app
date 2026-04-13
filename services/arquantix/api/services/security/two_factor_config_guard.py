"""Fail-fast validation of 2FA configuration in production-like environments."""
from __future__ import annotations

import logging
import os

from services.security.providers.email_provider import get_email_provider
from services.security.providers.sms_provider import get_sms_provider
from services.security.two_factor_env import is_production_like_env

logger = logging.getLogger(__name__)


class TwoFactorConfigGuardError(RuntimeError):
    """Raised when mandatory 2FA configuration is missing in production."""


def run_two_factor_config_guard() -> None:
    """
    Call from application startup (non-testing). No-op unless APP_ENV/ARQUANTIX_ENV
    is production-like, unless SKIP_TWO_FACTOR_CONFIG_GUARD is set.
    """
    if os.getenv("SKIP_TWO_FACTOR_CONFIG_GUARD", "").lower() in ("1", "true", "yes"):
        logger.warning("SKIP_TWO_FACTOR_CONFIG_GUARD set — 2FA boot guard skipped")
        return
    if not is_production_like_env():
        return

    errors: list[str] = []

    if os.getenv("FAKE_SMS_PROVIDER", "").strip().lower() in ("1", "true", "yes"):
        errors.append(
            "FAKE_SMS_PROVIDER must not be enabled in production-like environments "
            "(simulated SMS is dev/test only)."
        )

    if os.getenv("TWO_FACTOR_REQUIRE_AUTH", "true").lower() not in ("1", "true", "yes"):
        errors.append(
            "TWO_FACTOR_REQUIRE_AUTH must be true when APP_ENV is production/staging "
            "(dev-only person_id body would otherwise be a critical risk)."
        )

    totp_key = (os.getenv("TWO_FACTOR_TOTP_MASTER_KEY") or "").strip()
    if len(totp_key) < 32:
        errors.append(
            "TWO_FACTOR_TOTP_MASTER_KEY must be set (at least 32 characters) in production; "
            "do not rely on JWT_SECRET_KEY for TOTP envelope encryption."
        )

    sms = get_sms_provider()
    if getattr(sms, "is_noop", True):
        errors.append(
            "Operational SMS provider required in production (set TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER). Noop SMS is not allowed."
        )

    email = get_email_provider()
    if getattr(email, "is_noop", True):
        errors.append(
            "Operational email provider required in production (set SES_FROM_EMAIL or AWS_SES_FROM). "
            "Noop email is not allowed."
        )

    if errors:
        for msg in errors:
            logger.critical("2FA boot blocked: %s", msg)
        raise TwoFactorConfigGuardError(
            "Invalid 2FA production configuration:\n- " + "\n- ".join(errors)
        )

    logger.info("2FA configuration guard passed for production-like environment")
