"""E.164 phone normalization for registration and verification (delegates to phone_validation)."""
from __future__ import annotations

import re
from typing import Any, Optional

from .phone_validation import normalize_to_e164 as _normalize_to_e164


def normalize_e164_phone(value: Any) -> Optional[str]:
    """Strict E.164 already normalized (+ and digits only)."""
    if value is None:
        return None
    s = str(value).strip().replace(" ", "")
    if not s:
        return None
    if not s.startswith("+"):
        return None
    if len(s) < 10:
        return None
    if not re.match(r"^\+\d{8,15}$", s):
        return None
    return s


def normalize_to_e164(
    value: Any,
    *,
    default_region: Optional[str] = None,
) -> Optional[str]:
    """Normalize to E.164 using libphonenumber + mobile/SMS-capable rules."""
    reg = (default_region or "FR").strip().upper()
    if len(reg) != 2 or not reg.isalpha():
        reg = "FR"
    return _normalize_to_e164(
        value,
        selected_country_iso2=None,
        jurisdiction_default_region=reg,
    )


normalize_phone_to_e164 = normalize_to_e164
