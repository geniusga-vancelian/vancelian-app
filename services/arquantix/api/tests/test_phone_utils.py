"""Tests for services.registration.phone_utils.normalize_to_e164."""
from __future__ import annotations

import pytest

from services.registration.phone_utils import normalize_to_e164


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0651624864", "+33651624864"),
        ("06 51 62 48 64", "+33651624864"),
        ("+33651624864", "+33651624864"),
        ("+330651624864", "+33651624864"),
        ("+33 06 51 62 48 64", "+33651624864"),
    ],
)
def test_normalize_fr_mobile_variants(raw: str, expected: str) -> None:
    assert normalize_to_e164(raw, default_region="FR") == expected


def test_normalize_invalid_returns_none() -> None:
    assert normalize_to_e164("12", default_region="FR") is None
    assert normalize_to_e164("abc", default_region="FR") is None
