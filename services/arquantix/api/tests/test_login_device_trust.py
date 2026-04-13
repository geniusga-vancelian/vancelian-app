"""Tests device trust profil + évaluation contexte login (sans moteur SIEM parallèle)."""
from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import timedelta

import pytest
from starlette.requests import Request
from sqlalchemy.orm import Session

from auth import get_password_hash
from database import (
    AdminUser,
    AuthDeviceBlacklist,
    AuthGlobalRiskScore,
    AuthPasskey,
    AuthUserDeviceProfile,
)
from services.auth.refresh_session import _utcnow
from services.security.device_reputation.device_identity import build_device_hash
from services.security.login_auth_strategy_service import decide_login_auth_strategy
from services.security.login_context_risk import evaluate_login_context_risk
from services.security.login_device_trust_service import (
    DeviceTrustComputationInput,
    compute_device_trust_level,
    compute_device_trust_score,
    update_user_device_profile_on_login,
)


def _headers_to_scope(headers: dict) -> list:
    out = []
    for k, v in headers.items():
        out.append((k.lower().encode("ascii"), str(v).encode("utf-8")))
    return out


def _make_request(
    *,
    device_id: str = "dev-unit-1",
    fingerprint: str | None = "ab" * 32,
    country: str | None = None,
) -> Request:
    h = {
        "x-device-id": device_id,
    }
    if fingerprint:
        h["x-device-fingerprint"] = json.dumps({"device_id": fingerprint})
    if country:
        h["cf-ipcountry"] = country
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/login/sms/start",
        "headers": _headers_to_scope(h),
        "client": ("203.0.113.9", 1234),
    }
    return Request(scope)


@pytest.fixture
def user_a(db: Session) -> AdminUser:
    u = AdminUser(
        email=f"trust-{uuid.uuid4().hex[:8]}@test.dev",
        hashed_password=get_password_hash("pw"),
        mobile_e164="+33600000001",
    )
    db.add(u)
    db.flush()
    return u


def test_compute_device_trust_known_device_high(db: Session, user_a: AdminUser, monkeypatch):
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "true")
    dh = build_device_hash("dev-stable", "cd" * 32, None)
    prof = AuthUserDeviceProfile(
        id=uuid.uuid4(),
        user_id=user_a.id,
        device_hash=dh,
        device_id="dev-stable",
        fingerprint_hash="cd" * 32,
        first_seen_at=_utcnow() - timedelta(days=20),
        last_seen_at=_utcnow(),
        login_count=40,
        successful_login_count=38,
        failed_login_count=1,
        trust_score=0,
        trust_level="LOW",
    )
    db.add(prof)
    db.flush()

    r = evaluate_login_context_risk(
        db,
        user_a,
        device_hash=dh,
        device_id_normalized="dev-stable",
        fingerprint_hash="cd" * 32,
        ip_address="203.0.113.9",
        country_code="FR",
        attestation_trusted=False,
    )
    assert r["device_trust_score"] >= 60
    assert r["device_trust_level"] in ("HIGH", "MEDIUM")
    assert r["decision_hint"] in ("otp_only", "passkey_preferred")


def test_new_device_low_trust_step_up(db: Session, user_a: AdminUser, monkeypatch):
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "true")
    dh = build_device_hash("brand-new", "ef" * 32, None)
    r = evaluate_login_context_risk(
        db,
        user_a,
        device_hash=dh,
        device_id_normalized="brand-new",
        fingerprint_hash="ef" * 32,
        ip_address="198.51.100.2",
        country_code="FR",
        attestation_trusted=False,
    )
    assert "new_user_device_profile" in r["signals"]
    assert r["device_trust_level"] == "LOW"
    assert r["decision_hint"] in ("otp_step_up", "passkey_preferred", "blocked")


def test_fingerprint_change_signal(db: Session, user_a: AdminUser, monkeypatch):
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "true")
    dh = build_device_hash("dev-fp", "11" * 32, None)
    prof = AuthUserDeviceProfile(
        id=uuid.uuid4(),
        user_id=user_a.id,
        device_hash=dh,
        device_id="dev-fp",
        fingerprint_hash="11" * 32,
        first_seen_at=_utcnow() - timedelta(days=5),
        last_seen_at=_utcnow(),
        login_count=5,
        successful_login_count=5,
        failed_login_count=0,
        trust_score=50,
        trust_level="MEDIUM",
    )
    db.add(prof)
    db.flush()

    r = evaluate_login_context_risk(
        db,
        user_a,
        device_hash=dh,
        device_id_normalized="dev-fp",
        fingerprint_hash="22" * 32,
        ip_address="203.0.113.9",
        country_code="FR",
        attestation_trusted=False,
    )
    assert "fingerprint_changed_or_missing_vs_profile" in r["signals"]


def test_blacklisted_device_blocked(db: Session, user_a: AdminUser, monkeypatch):
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "true")
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "true")
    dh = build_device_hash("dev-blk", "aa" * 32, None)
    db.add(
        AuthDeviceBlacklist(
            id=uuid.uuid4(),
            device_hash=dh,
            reason="unit_test",
            blocked_until=None,
        )
    )
    db.flush()

    r = evaluate_login_context_risk(
        db,
        user_a,
        device_hash=dh,
        device_id_normalized="dev-blk",
        fingerprint_hash="aa" * 32,
        ip_address="203.0.113.9",
        country_code="FR",
        attestation_trusted=False,
    )
    assert r["decision_hint"] == "blocked"
    assert "device_blacklisted" in r["signals"]
    assert r["login_risk_score"] >= 96


def test_decide_step_up_suspect(monkeypatch, db: Session, user_a: AdminUser):
    monkeypatch.setenv("LOGIN_AUTH_STRATEGY_ENABLED", "true")
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "true")
    db.add(
        AuthGlobalRiskScore(user_id=user_a.id, score=55, level="HIGH", updated_at=_utcnow())
    )
    db.flush()

    req = _make_request(device_id="suspect-1", fingerprint="ff" * 32)
    out = decide_login_auth_strategy(db, req, user_a, device_header="suspect-1", attestation_trusted=False)
    assert out.step_up_required or out.primary_method == "passkey"
    assert not out.blocked


def test_decide_passkey_preferred_when_enrolled(db: Session, user_a: AdminUser, monkeypatch):
    monkeypatch.setenv("LOGIN_AUTH_STRATEGY_ENABLED", "true")
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "true")
    db.add(
        AuthPasskey(
            id=uuid.uuid4(),
            user_id=user_a.id,
            credential_id_b64="dGVzdGNyZWRpZA",
            public_key_b64="dGVzdGtleQ",
            sign_count=1,
        )
    )
    db.flush()
    req = _make_request(device_id="new-pk", fingerprint="ee" * 32)
    out = decide_login_auth_strategy(db, req, user_a, device_header="new-pk", attestation_trusted=False)
    assert out.primary_method == "passkey"


def test_update_profile_increments_counters(db: Session, user_a: AdminUser):
    dh = build_device_hash("cnt-dev", "99" * 32, None)
    p = update_user_device_profile_on_login(
        db,
        user=user_a,
        device_hash=dh,
        device_id_normalized="cnt-dev",
        fingerprint_hash="99" * 32,
        ip_address="1.1.1.1",
        country_code="DE",
        success=True,
        auth_strength="otp",
        attestation_trusted=False,
    )
    assert p.successful_login_count == 1
    p2 = update_user_device_profile_on_login(
        db,
        user=user_a,
        device_hash=dh,
        device_id_normalized="cnt-dev",
        fingerprint_hash="99" * 32,
        ip_address="1.1.1.1",
        country_code="DE",
        success=False,
        auth_strength="otp",
        attestation_trusted=False,
    )
    assert p2.failed_login_count == 1


def test_trust_score_monotonic_components():
    base = DeviceTrustComputationInput(
        days_since_first_seen=10,
        successful_login_count=10,
        failed_login_count=0,
        fingerprint_stable=True,
        ip_country_stable=True,
        attestation_trusted=False,
        device_reputation_risk_0_100=0,
        reputation_level="LOW",
    )
    s0 = compute_device_trust_score(base)
    s_att = compute_device_trust_score(replace(base, attestation_trusted=True))
    assert s_att > s0
    s_unstable = compute_device_trust_score(replace(base, fingerprint_stable=False))
    assert s_unstable < s0
    assert compute_device_trust_level(80) == "HIGH"
