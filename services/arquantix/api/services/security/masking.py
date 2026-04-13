"""Mask phone/email for API responses (never log OTP codes)."""
from __future__ import annotations

import re
from typing import Optional


def mask_phone_e164(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return value
    digits = re.sub(r"\D", "", value)
    if len(digits) < 4:
        return "****"
    return f"***{digits[-4:]}"


def mask_email(value: Optional[str]) -> Optional[str]:
    if not value or "@" not in value:
        return "****"
    local, _, domain = value.partition("@")
    if not local:
        return f"****@{domain}"
    shown = local[0] + "***" if len(local) > 1 else "*"
    return f"{shown}@{domain}"
