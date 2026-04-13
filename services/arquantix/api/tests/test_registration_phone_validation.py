"""Strict phone_validation tests (MOBILE-only in production-like mode)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import services.registration.phone_validation as pv
from services.registration.phone_validation import (
    classify_phone_number,
    default_phone_region_iso2,
    parse_phone_input,
    validate_mobile_phone_basic,
    validate_mobile_phone_for_jurisdiction,
)


def test_default_region_eu_uae_de():
    assert default_phone_region_iso2("EU") == "FR"
    assert default_phone_region_iso2("UAE") == "AE"
    assert default_phone_region_iso2("DE") == "DE"


def test_default_region_unknown_returns_none():
    assert default_phone_region_iso2("ACME_CORP") is None


@pytest.mark.parametrize(
    "raw",
    [
        "+33612345678",
        "+4915123456789",
        "+34612345678",
        "+393401234567",
        "+971501234567",
    ],
)
def test_mobile_accepted_e164_eu_ae(raw: str):
    r = validate_mobile_phone_basic(raw)
    assert r.ok, f"{raw} -> {r.error_code} {r.user_message}"
    assert r.normalized_e164 == raw
    assert r.is_mobile_compatible is True
    assert r.risk_signal == "LOW"


def test_fr_landline_rejected():
    r = validate_mobile_phone_basic("+33123456789")
    assert not r.ok
    assert r.error_code == "phone_number_not_mobile"
    assert r.risk_signal == "BLOCKED"


def test_us_toll_free_rejected():
    r = validate_mobile_phone_basic("+18005551234")
    assert not r.ok
    assert r.error_code == "phone_number_not_mobile"


def test_mexico_fixed_line_or_mobile_rejected_when_production_like(monkeypatch):
    monkeypatch.setattr(pv, "_is_production_like", lambda: True)
    r = validate_mobile_phone_basic("+525512345678")
    assert not r.ok
    assert r.error_code == "phone_number_not_mobile"


def test_mexico_relaxed_only_nonprod_debug_env(monkeypatch):
    monkeypatch.setattr(pv, "_is_production_like", lambda: False)
    monkeypatch.setattr(pv, "phone_validation_debug_enabled", lambda: True)
    monkeypatch.setenv("PHONE_ALLOW_FIXED_LINE_OR_MOBILE", "true")
    r = validate_mobile_phone_basic("+525512345678")
    assert r.ok
    assert r.normalized_e164 == "+525512345678"


def test_garbage_rejected():
    r = validate_mobile_phone_basic("abc")
    assert not r.ok
    assert r.error_code == "invalid_phone_number"
    assert r.risk_signal == "BLOCKED"


def test_fr_national_requires_region():
    r = validate_mobile_phone_basic("0612345678", jurisdiction_default_region="FR")
    assert r.ok
    assert r.normalized_e164 == "+33612345678"


def test_national_without_region_or_plus_fails():
    r = validate_mobile_phone_basic("0612345678", jurisdiction_default_region=None)
    assert not r.ok
    assert r.error_code == "invalid_phone_number"


def test_parse_e164_direct():
    num, err, compact0 = parse_phone_input("+33612345678", None)
    assert err is None and num is not None
    assert compact0 == "+33612345678"


def test_classify_valid_mobile():
    c = classify_phone_number("+33612345678")
    assert c.ok
    assert c.is_mobile_compatible
    assert c.normalized_e164 == "+33612345678"


def test_fr_plus330_hint_when_invalid():
    r = validate_mobile_phone_basic("+3300abc")
    assert not r.ok
    assert r.message_hint is not None
    assert "leading 0" in (r.message_hint or "").lower()


def test_selected_country_mismatch_fr_de():
    db = MagicMock()
    r = validate_mobile_phone_for_jurisdiction(
        db,
        "+33612345678",
        "EU",
        selected_country_iso2="DE",
        enforce_jurisdiction_allowlist=False,
    )
    assert not r.ok
    assert r.error_code == "phone_country_mismatch"
    assert r.risk_signal == "BLOCKED"


def test_jurisdiction_success_risk_signal_low():
    db = MagicMock()
    r = validate_mobile_phone_for_jurisdiction(
        db,
        "+33612345678",
        "EU",
        selected_country_iso2="FR",
        enforce_jurisdiction_allowlist=False,
    )
    assert r.ok
    assert r.risk_signal == "LOW"
