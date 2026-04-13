"""Central masking for registration execution / audit payloads.

All sensitive values in execution event payloads MUST go through this module.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional, Set

# Slug substrings → treat value as sensitive (case-insensitive)
_SENSITIVE_SLUG_MARKERS: tuple[str, ...] = (
    "email",
    "mail",
    "phone",
    "mobile",
    "tel",
    "iban",
    "password",
    "secret",
    "token",
    "ssn",
    "national_id",
    "id_number",
    "tax_id",
)

# Exact slug matches (lowercase)
_SENSITIVE_SLUGS_EXACT: Set[str] = {
    "password",
    "secret",
}


def _slug_is_sensitive(slug: str) -> bool:
    s = (slug or "").lower()
    if s in _SENSITIVE_SLUGS_EXACT:
        return True
    return any(m in s for m in _SENSITIVE_SLUG_MARKERS)


def mask_email(value: Any) -> Any:
    if value is None or not isinstance(value, str) or "@" not in value:
        return value if value is None else "[redacted]"
    local, _, domain = value.partition("@")
    if not local:
        return "[redacted]"
    shown = local[0] + "***" if len(local) > 1 else "*"
    return f"{shown}@{domain}"


_PHONE_DIGITS_RE = re.compile(r"\d")


def mask_phone(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return mask_scalar(value)
    digits = _PHONE_DIGITS_RE.findall(value)
    if len(digits) < 4:
        return "[redacted]"
    tail = "".join(digits[-4:])
    return f"***{tail}"


def mask_date_like(value: Any) -> Any:
    """Keep year only for ISO-like dates when string."""
    if value is None or not isinstance(value, str):
        return value
    if len(value) >= 4 and value[:4].isdigit():
        return value[:4] + "-**-**"
    return "[date_redacted]"


def mask_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) <= 2:
            return "*"
        return value[0] + "***" + value[-1] if len(value) > 2 else "**"
    if isinstance(value, (list, dict)):
        return "[complex_redacted]"
    return "[redacted]"


def mask_slug_value(slug: str, value: Any) -> Any:
    """Mask a single field value using slug heuristics."""
    if value is None:
        return None
    s = (slug or "").lower()
    if "email" in s or s.endswith("mail"):
        return mask_email(value)
    if "phone" in s or "mobile" in s or s == "tel" or "tel_" in s:
        return mask_phone(value)
    if "birth" in s or "dob" in s or "date_of_birth" in s:
        return mask_date_like(value)
    if _slug_is_sensitive(slug):
        return mask_scalar(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and len(value) > 200:
        return value[:80] + "…[truncated]"
    return value


def mask_answers_for_audit(answers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Mask all answers keyed by field slug for execution payloads."""
    if not answers:
        return {}
    return {
        k: mask_slug_value(k, v)
        for k, v in answers.items()
        if not str(k).startswith("__")
    }


def mask_context_subset(context: Dict[str, Any], fields: Iterable[str]) -> Dict[str, Any]:
    """Build a dict of referenced rule fields with masking."""
    out: Dict[str, Any] = {}
    for f in fields:
        if f in context:
            out[f] = mask_slug_value(f, context[f])
    return out
