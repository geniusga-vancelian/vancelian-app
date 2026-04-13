"""PR E — politique attestation obligatoire (flags désactivés par défaut)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.auth.device_attestation_pr_e_policy import (
    device_attestation_required_login,
    device_attestation_required_sensitive,
)
from services.auth.device_attestation_trust import (
    TRUST_TIER_HIGH,
    TRUST_TIER_LOW,
    TRUST_TIER_MEDIUM,
    compute_attestation_trust_level,
    is_attestation_stale,
    tier_rank,
)
from services.auth.device_attestation_service import AttestationResult, TRUST_HIGH as C_HIGH


def test_compute_tier_high_from_valid_result():
    r = AttestationResult(True, C_HIGH, [], "apple_app_attest", {"k": 1})
    t = compute_attestation_trust_level(
        attestation_verified_at=None,
        attestation_type=None,
        attestation_metadata={},
        credential_has_attestation_bound=True,
        attestation_result=r,
    )
    assert t == TRUST_TIER_HIGH


def test_compute_tier_low_invalid():
    r = AttestationResult(False, "LOW", ["x"], None, {})
    t = compute_attestation_trust_level(
        attestation_verified_at=None,
        attestation_type=None,
        attestation_metadata={},
        credential_has_attestation_bound=False,
        attestation_result=r,
    )
    assert t == TRUST_TIER_LOW


def test_is_attestation_stale_true_when_old():
    old = datetime.now(timezone.utc) - timedelta(days=2)
    assert is_attestation_stale(attestation_verified_at=old, max_age_sec=3600)


def test_tier_rank_ordering():
    assert tier_rank(TRUST_TIER_HIGH) > tier_rank(TRUST_TIER_MEDIUM) > tier_rank(TRUST_TIER_LOW)


def test_flags_default_off():
    assert device_attestation_required_login() is False
    assert device_attestation_required_sensitive() is False
