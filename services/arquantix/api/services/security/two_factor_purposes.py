"""Allowlisted 2FA purposes (prod)."""
from __future__ import annotations

from typing import FrozenSet

# Canonical purposes supported in production. Keep legacy aliases for backward compatibility.
ALLOWED_PURPOSES: FrozenSet[str] = frozenset(
    {
        "verify_phone",
        "verify_email",
        "withdrawal",  # legacy alias; prefer external_withdrawal for new flows
        "external_withdrawal",
        "security_change",
        "login_step_up",
        "login",
        "totp_setup",
    }
)


def validate_purpose(purpose: str, *, relaxed: bool) -> None:
    from services.security.two_factor_exceptions import TwoFactorException

    p = (purpose or "").strip()
    if not p:
        raise TwoFactorException("invalid_purpose", "purpose is required")
    if relaxed:
        return
    if p not in ALLOWED_PURPOSES:
        raise TwoFactorException(
            "purpose_not_allowed",
            "This verification type is not available",
        )
