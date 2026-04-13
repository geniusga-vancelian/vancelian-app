"""PR E — modèle de confiance attestation (LOW / MEDIUM / HIGH) pour enforcement."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.auth.device_attestation_service import (
    TRUST_HIGH as ATTEST_CRYPTO_HIGH,
    TRUST_MEDIUM as ATTEST_CRYPTO_MEDIUM,
    TRUST_LOW as ATTEST_CRYPTO_LOW,
    AttestationResult,
)

TRUST_TIER_HIGH = "HIGH"
TRUST_TIER_MEDIUM = "MEDIUM"
TRUST_TIER_LOW = "LOW"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def attestation_tier_high_max_age_sec() -> int:
    try:
        return max(300, min(86400 * 14, int(os.getenv("DEVICE_ATTESTATION_TIER_HIGH_MAX_AGE_SEC", "86400"))))
    except ValueError:
        return 86400


def attestation_tier_medium_max_age_sec() -> int:
    try:
        return max(3600, min(86400 * 30, int(os.getenv("DEVICE_ATTESTATION_TIER_MEDIUM_MAX_AGE_SEC", "604800"))))
    except ValueError:
        return 604800


def compute_attestation_trust_level(
    *,
    attestation_verified_at: Optional[datetime],
    attestation_type: Optional[str],
    attestation_metadata: Optional[Dict[str, Any]],
    credential_has_attestation_bound: bool,
    attestation_result: Optional[AttestationResult] = None,
    now: Optional[datetime] = None,
) -> str:
    """
    Niveau métier distinct du ``device_trust_level`` session (TRUSTED/UNKNOWN/…).

    - **HIGH** : attestation cryptographique forte + signal récent + liaison clé si attendue.
    - **MEDIUM** : attestation valide mais ancienne, ou cryptographiquement « medium ».
    - **LOW** : aucun signal fiable.
    """
    now = now or _now_utc()
    meta = attestation_metadata or {}

    if attestation_result is not None:
        if not attestation_result.is_valid:
            return TRUST_TIER_LOW
        crypto = (attestation_result.trust_level or "").strip().upper()
        if crypto == ATTEST_CRYPTO_HIGH:
            tier_candidate = TRUST_TIER_HIGH
        elif crypto == ATTEST_CRYPTO_MEDIUM:
            tier_candidate = TRUST_TIER_MEDIUM
        else:
            tier_candidate = TRUST_TIER_LOW
        if tier_candidate == TRUST_TIER_HIGH and not credential_has_attestation_bound:
            tier_candidate = TRUST_TIER_MEDIUM
        return tier_candidate

    if attestation_verified_at is None:
        return TRUST_TIER_LOW

    if attestation_verified_at.tzinfo is None:
        verified = attestation_verified_at.replace(tzinfo=timezone.utc)
    else:
        verified = attestation_verified_at
    age_sec = (now - verified).total_seconds()
    if age_sec < 0:
        age_sec = 0

    high_age = attestation_tier_high_max_age_sec()
    med_age = attestation_tier_medium_max_age_sec()

    crypto_from_session = (meta.get("trust_level") or meta.get("tier") or "").strip().upper()
    if not crypto_from_session and attestation_type:
        crypto_from_session = TRUST_TIER_HIGH if "app_attest" in attestation_type.lower() else ""

    if age_sec <= high_age:
        if credential_has_attestation_bound and (
            crypto_from_session in (TRUST_TIER_HIGH, "TRUSTED", ATTEST_CRYPTO_HIGH)
            or "integrity" in (attestation_type or "").lower()
            or "app_attest" in (attestation_type or "").lower()
        ):
            return TRUST_TIER_HIGH
        if attestation_type:
            return TRUST_TIER_MEDIUM
        return TRUST_TIER_LOW

    if age_sec <= med_age and attestation_type:
        return TRUST_TIER_MEDIUM

    return TRUST_TIER_LOW


def is_attestation_stale(
    *,
    attestation_verified_at: Optional[datetime],
    max_age_sec: int,
    now: Optional[datetime] = None,
) -> bool:
    """True si pas de date ou plus vieux que ``max_age_sec``."""
    if attestation_verified_at is None:
        return True
    now = now or _now_utc()
    v = attestation_verified_at
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return (now - v).total_seconds() > max_age_sec


def tier_rank(tier: str) -> int:
    m = (tier or "").strip().upper()
    if m == TRUST_TIER_HIGH:
        return 3
    if m == TRUST_TIER_MEDIUM:
        return 2
    if m == TRUST_TIER_LOW:
        return 1
    return 0
