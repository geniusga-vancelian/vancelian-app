"""Environment classification for 2FA (prod vs relaxed dev/test).

Délègue la classification déploiement à :mod:`services.security.security_env`.
Les valeurs sont lues à l’appel pour permettre aux tests de muter ``os.environ``.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from services.security.security_env import (
    get_normalized_app_env,
    is_production_like_env,
    is_two_factor_relaxed,
    should_expose_dev_otp_code,
)

_DEV_OTP_RE = re.compile(r"^\d{6}$")


def effective_app_env() -> str:
    """Alias historique : retourne l’environnement **normalisé** (voir ``get_normalized_app_env``)."""
    return get_normalized_app_env()


def two_factor_dev_fixed_code() -> Optional[str]:
    """Six-digit OTP from TWO_FACTOR_DEV_FIXED_CODE when env is not production-like.

    Invalid format → ignored (None).
    """
    if is_production_like_env():
        return None
    raw = (os.getenv("TWO_FACTOR_DEV_FIXED_CODE") or "").strip()
    if not raw or not _DEV_OTP_RE.match(raw):
        return None
    return raw


def two_factor_dev_code_for_api_exposure() -> Optional[str]:
    """Plain dev OTP for JSON `dev_code` when explicitly enabled."""
    if not should_expose_dev_otp_code():
        return None
    return two_factor_dev_fixed_code()


def admin_email_otp_dev_code_for_response(plaintext: str) -> Optional[str]:
    """Expose the issued OTP in JSON for admin email login start (dev tooling only)."""
    if is_production_like_env():
        return None
    if not should_expose_dev_otp_code():
        return None
    return plaintext


__all__ = [
    "effective_app_env",
    "is_production_like_env",
    "is_two_factor_relaxed",
    "two_factor_dev_fixed_code",
    "two_factor_dev_code_for_api_exposure",
    "admin_email_otp_dev_code_for_response",
]
