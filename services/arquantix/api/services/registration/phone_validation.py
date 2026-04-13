"""Centralized phone parsing / E.164 / **strict MOBILE-only** validation (libphonenumber).

The API is the **only** source of truth for parse, normalize, type checks, and policy.

Submit payload (per binding slug):

- ``{slug}_raw`` (preferred) or legacy ``{slug}``
- ``{slug}_country_iso2`` or legacy ``{slug}_country_code`` (ISO alpha-2)

Validation order (strict):

1. Parse (E.164 with ``None`` region; national only with explicit ISO2 hint or
   jurisdiction-derived default when mappable).
2. ``is_possible_number``
3. ``is_valid_number``
4. ``number_type == MOBILE`` (only). All other lib types are rejected.
5. Selected-country consistency (if ISO2 provided).
6. Jurisdiction phone allowlist (if configured).

Debug-only relaxation (never in production-like environments):

- When ``ENVIRONMENT`` / ``APP_ENV`` is **not** ``production``/``prod``/``live``,
  and ``PHONE_VALIDATION_DEBUG`` is true, and ``PHONE_ALLOW_FIXED_LINE_OR_MOBILE``
  is true, ``FIXED_LINE_OR_MOBILE`` is also accepted (QA only).

``PHONE_VALIDATION_DEBUG``: adds structured ``debug`` keys on structured 422 responses
(``normalized``, ``region``, ``type``, ``allowed``) — disable in production.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional, Tuple

import phonenumbers
from phonenumbers import NumberParseException
from phonenumbers.phonenumberutil import region_code_for_number
from sqlalchemy.orm import Session

# Strict product policy: only MOBILE is SMS-eligible in production.
ALLOWED_PHONE_TYPES: FrozenSet[int] = frozenset({phonenumbers.PhoneNumberType.MOBILE})

# Regions treated as "LOW" risk signal for accepted mobiles (EU product + EEA + CH + UK + AE).
_RISK_LOW_REGIONS: FrozenSet[str] = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IS",
        "IT",
        "LI",
        "LT",
        "LU",
        "LV",
        "MT",
        "NL",
        "NO",
        "PL",
        "PT",
        "RO",
        "SE",
        "SI",
        "SK",
        "ES",
        "CH",
        "GB",
        "AE",
    }
)

USER_MESSAGES = {
    "invalid_phone_number": "Please enter a valid mobile number.",
    "phone_number_not_mobile": (
        "Please use a mobile number that can receive SMS codes."
    ),
    "unsupported_phone_country": (
        "This phone number is not supported for your jurisdiction."
    ),
    "phone_country_mismatch": (
        "The phone number does not match the selected country."
    ),
}

_FR_LEADING_ZERO_AFTER_CC_HINT = (
    "Please enter your number without the leading 0 after the country code."
)


def _is_production_like() -> bool:
    from services.security.security_env import is_phone_validation_production_strict

    return is_phone_validation_production_strict()


def phone_validation_debug_enabled() -> bool:
    return os.environ.get("PHONE_VALIDATION_DEBUG", "").lower().strip() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _lib_types_accepted_for_sms() -> FrozenSet[int]:
    """MOBILE only in production; optional FL_OR_MOBILE in non-prod QA when debug flags set."""
    if not _is_production_like():
        if phone_validation_debug_enabled():
            v = os.environ.get("PHONE_ALLOW_FIXED_LINE_OR_MOBILE", "").lower().strip()
            if v in ("1", "true", "yes", "on"):
                return frozenset(
                    {
                        phonenumbers.PhoneNumberType.MOBILE,
                        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
                    }
                )
    return ALLOWED_PHONE_TYPES


def _is_strict_mobile_type(ntype: int) -> bool:
    return ntype in _lib_types_accepted_for_sms()


def risk_signal_accepted(region_code: Optional[str], jurisdiction_code: str) -> str:
    """Post-success heuristic for future scoring (not yet enforced as a gate)."""
    jc = (jurisdiction_code or "").strip().upper()
    if jc == "EU":
        return "LOW"
    if jc == "UAE" or region_code == "AE":
        return "LOW"
    if region_code and region_code in _RISK_LOW_REGIONS:
        return "LOW"
    if region_code:
        return "MEDIUM"
    return "MEDIUM"


def default_phone_region_iso2(jurisdiction_code: str) -> Optional[str]:
    """Map product jurisdiction code to a default ISO2 hint for national-format input.

    Returns ``None`` when no deterministic default exists (national numbers then
    require a selected country ISO2 or E.164 ``+`` input).
    """
    jc = (jurisdiction_code or "").strip().upper()
    if jc == "EU":
        return "FR"
    if jc == "UAE":
        return "AE"
    if len(jc) == 2 and jc.isalpha():
        return jc
    return None


def _strip_fr_duplicate_zero_after_country_code(compact: str) -> str:
    if compact.startswith("+330") and len(compact) > 4:
        return "+33" + compact[4:]
    return compact


def _compact_raw(value: str) -> str:
    return re.sub(r"[\s\-.()]", "", value.strip())


def _fr_hint_for_compact(compact_before_strip: str) -> Optional[str]:
    if re.match(r"^\+330\d", compact_before_strip or ""):
        return _FR_LEADING_ZERO_AFTER_CC_HINT
    return None


def _normalize_selected_iso2(selected_country_iso2: Optional[str]) -> Optional[str]:
    sel = (selected_country_iso2 or "").strip().upper()
    if len(sel) == 2 and sel.isalpha():
        return sel
    return None


def parse_phone_input(
    raw_value: Any,
    selected_country_iso2: Optional[str],
    *,
    jurisdiction_default_region: Optional[str] = None,
) -> Tuple[Optional[phonenumbers.PhoneNumber], Optional[str], str]:
    """Parse user input; on failure returns ``(None, reason, original_compact)``."""
    if raw_value is None:
        return None, "empty", ""
    s = str(raw_value).strip()
    if not s:
        return None, "empty", ""
    compact0 = _compact_raw(s)
    if not compact0:
        return None, "empty", ""
    compact = _strip_fr_duplicate_zero_after_country_code(compact0)

    region_hint = _normalize_selected_iso2(selected_country_iso2)
    if not region_hint:
        reg = (jurisdiction_default_region or "").strip().upper()
        if len(reg) == 2 and reg.isalpha():
            region_hint = reg

    if not compact.startswith("+") and not region_hint:
        return None, "parse_error", compact0

    try:
        if compact.startswith("+"):
            num = phonenumbers.parse(compact, None)
        else:
            num = phonenumbers.parse(compact, region_hint)
    except NumberParseException:
        return None, "parse_error", compact0
    return num, None, compact0


def normalize_phone_to_e164(
    raw_value: Any,
    *,
    selected_country_iso2: Optional[str] = None,
    jurisdiction_default_region: Optional[str] = None,
) -> Optional[str]:
    res = validate_mobile_phone_basic(
        raw_value,
        selected_country_iso2=selected_country_iso2,
        jurisdiction_default_region=jurisdiction_default_region,
    )
    return res.normalized_e164 if res.ok else None


@dataclass(frozen=True)
class PhoneValidationResult:
    ok: bool
    raw_input: str
    selected_country_iso2: Optional[str]
    normalized_e164: Optional[str]
    region_code: Optional[str]
    country_calling_code: Optional[int]
    number_type: Optional[int]
    is_possible: bool
    is_valid: bool
    is_mobile_compatible: bool
    is_policy_allowed: bool
    error_code: Optional[str]
    user_message: Optional[str]
    message_hint: Optional[str]
    debug: Optional[Dict[str, Any]]
    risk_signal: str

    @property
    def technical_detail(self) -> str:
        return self.user_message or ""


def classify_phone_number(
    raw_value: Any,
    selected_country_iso2: Optional[str] = None,
    *,
    jurisdiction_default_region: Optional[str] = None,
) -> PhoneValidationResult:
    """Lib metrics only; ``is_policy_allowed`` is false; not for jurisdiction gates."""
    raw_display = "" if raw_value is None else str(raw_value).strip()
    sel = _normalize_selected_iso2(selected_country_iso2)

    num, err, compact0 = parse_phone_input(
        raw_value,
        selected_country_iso2,
        jurisdiction_default_region=jurisdiction_default_region,
    )
    if err or num is None:
        ec = "invalid_phone_number"
        return PhoneValidationResult(
            False,
            raw_display,
            sel,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
            ec,
            USER_MESSAGES[ec],
            _fr_hint_for_compact(compact0) if err == "parse_error" else None,
            None,
            "BLOCKED",
        )

    poss = phonenumbers.is_possible_number(num)
    val = phonenumbers.is_valid_number(num)
    ntype = phonenumbers.number_type(num)
    region = region_code_for_number(num)
    e164 = (
        phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        if val
        else None
    )
    mob = _is_strict_mobile_type(ntype) if val else False
    ok_class = poss and val
    return PhoneValidationResult(
        ok_class,
        raw_display,
        sel,
        e164,
        region,
        num.country_code,
        ntype,
        poss,
        val,
        mob,
        False,
        None if ok_class else "invalid_phone_number",
        None if ok_class else USER_MESSAGES["invalid_phone_number"],
        _fr_hint_for_compact(compact0) if not ok_class else None,
        None,
        "BLOCKED" if not ok_class else ("LOW" if mob else "MEDIUM"),
    )


def validate_mobile_phone_basic(
    raw_value: Any,
    *,
    selected_country_iso2: Optional[str] = None,
    jurisdiction_default_region: Optional[str] = None,
) -> PhoneValidationResult:
    """Parse → possible → valid → strict MOBILE (see module doc)."""
    raw_display = "" if raw_value is None else str(raw_value).strip()
    sel = _normalize_selected_iso2(selected_country_iso2)

    num, err, compact0 = parse_phone_input(
        raw_value,
        selected_country_iso2,
        jurisdiction_default_region=jurisdiction_default_region,
    )
    if err or num is None:
        ec = "invalid_phone_number"
        hint = None
        if err == "parse_error":
            hint = _fr_hint_for_compact(compact0)
        return PhoneValidationResult(
            False,
            raw_display,
            sel,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
            ec,
            USER_MESSAGES[ec],
            hint,
            None,
            "BLOCKED",
        )

    poss = phonenumbers.is_possible_number(num)
    if not poss:
        return PhoneValidationResult(
            False,
            raw_display,
            sel,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
            "invalid_phone_number",
            USER_MESSAGES["invalid_phone_number"],
            _fr_hint_for_compact(compact0),
            None,
            "BLOCKED",
        )

    val = phonenumbers.is_valid_number(num)
    if not val:
        return PhoneValidationResult(
            False,
            raw_display,
            sel,
            None,
            region_code_for_number(num),
            num.country_code,
            phonenumbers.number_type(num),
            poss,
            False,
            False,
            False,
            "invalid_phone_number",
            USER_MESSAGES["invalid_phone_number"],
            _fr_hint_for_compact(compact0),
            None,
            "BLOCKED",
        )

    ntype = phonenumbers.number_type(num)
    if not _is_strict_mobile_type(ntype):
        return PhoneValidationResult(
            False,
            raw_display,
            sel,
            None,
            region_code_for_number(num),
            num.country_code,
            ntype,
            poss,
            val,
            False,
            False,
            "phone_number_not_mobile",
            USER_MESSAGES["phone_number_not_mobile"],
            None,
            None,
            "BLOCKED",
        )

    e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    region = region_code_for_number(num)
    return PhoneValidationResult(
        True,
        raw_display,
        sel,
        e164,
        region,
        num.country_code,
        ntype,
        poss,
        val,
        True,
        True,
        None,
        None,
        None,
        None,
        "LOW",
    )


def validate_mobile_phone_for_jurisdiction(
    db: Session,
    raw_value: Any,
    jurisdiction_code: str,
    *,
    selected_country_iso2: Optional[str],
    enforce_jurisdiction_allowlist: bool,
) -> PhoneValidationResult:
    """Strict chain including selected ISO2 and jurisdiction allowlist."""
    from .jurisdiction_policies import is_phone_country_allowed

    jc = (jurisdiction_code or "").strip().upper()
    default_reg = default_phone_region_iso2(jc)

    base = validate_mobile_phone_basic(
        raw_value,
        selected_country_iso2=selected_country_iso2,
        jurisdiction_default_region=default_reg,
    )
    if not base.ok:
        return base

    assert base.normalized_e164 is not None
    region = base.region_code

    sel = _normalize_selected_iso2(selected_country_iso2)
    if sel and region and sel != region:
        return PhoneValidationResult(
            False,
            base.raw_input,
            sel,
            None,
            region,
            base.country_calling_code,
            base.number_type,
            base.is_possible,
            base.is_valid,
            base.is_mobile_compatible,
            False,
            "phone_country_mismatch",
            USER_MESSAGES["phone_country_mismatch"],
            None,
            None,
            "BLOCKED",
        )

    if enforce_jurisdiction_allowlist and region:
        if not is_phone_country_allowed(db, jc, region):
            return PhoneValidationResult(
                False,
                base.raw_input,
                sel,
                None,
                region,
                base.country_calling_code,
                base.number_type,
                base.is_possible,
                base.is_valid,
                base.is_mobile_compatible,
                False,
                "unsupported_phone_country",
                USER_MESSAGES["unsupported_phone_country"],
                None,
                None,
                "HIGH",
            )

    rs = risk_signal_accepted(region, jc)
    return PhoneValidationResult(
        True,
        base.raw_input,
        sel,
        base.normalized_e164,
        base.region_code,
        base.country_calling_code,
        base.number_type,
        base.is_possible,
        base.is_valid,
        base.is_mobile_compatible,
        True,
        None,
        None,
        None,
        None,
        rs,
    )


def phone_validation_debug_dict(res: PhoneValidationResult) -> Dict[str, Any]:
    """422 ``debug`` object when ``PHONE_VALIDATION_DEBUG`` (contract keys)."""
    ntype_label = None
    if res.number_type is not None:
        try:
            ntype_label = phonenumbers.PhoneNumberType.to_string(res.number_type)
        except Exception:
            ntype_label = str(res.number_type)
    return {
        "normalized": res.normalized_e164,
        "region": res.region_code,
        "type": res.number_type,
        "type_label": ntype_label,
        "allowed": res.is_policy_allowed,
        "risk_signal": res.risk_signal,
        "is_mobile_compatible": res.is_mobile_compatible,
        "raw_input": res.raw_input,
        "selected_country_iso2": res.selected_country_iso2,
    }


def normalize_to_e164(
    raw_value: Any,
    *,
    selected_country_iso2: Optional[str] = None,
    jurisdiction_default_region: str = "FR",
) -> Optional[str]:
    """Backward-compatible alias used by ``phone_utils`` (explicit default region)."""
    reg: Optional[str] = jurisdiction_default_region.strip().upper()
    if len(reg) != 2 or not reg.isalpha():
        reg = "FR"
    return normalize_phone_to_e164(
        raw_value,
        selected_country_iso2=selected_country_iso2,
        jurisdiction_default_region=reg,
    )


def infer_region_iso2_from_e164(value: str) -> Optional[str]:
    s = str(value or "").strip()
    if not s.startswith("+"):
        return None
    try:
        num = phonenumbers.parse(s, None)
        if not phonenumbers.is_valid_number(num):
            return None
        return region_code_for_number(num)
    except NumberParseException:
        return None
