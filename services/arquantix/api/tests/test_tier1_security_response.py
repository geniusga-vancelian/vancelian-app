"""Tests Tier-1 : moteur de réponse risque, enforcement step-up, Play Integrity prod."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import cbor2
import pytest

from auth import create_access_token, enforce_access_security, get_password_hash
from database import AdminUser, AuthGlobalRiskScore, AuthSession
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from fastapi import HTTPException


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def engine_on(monkeypatch):
    monkeypatch.setenv("SECURITY_RESPONSE_ENGINE_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")


def test_recompute_score_72_requires_step_up(db, monkeypatch, engine_on):
    monkeypatch.setattr(
        "services.security.security_response_engine.compute_global_risk_score",
        lambda *_a, **_k: (72, "HIGH"),
    )
    u = AdminUser(email="tier1_step@test.dev", hashed_password=get_password_hash("pw"))
    db.add(u)
    db.flush()
    s = AuthSession(
        user_id=u.id,
        device_id="dev-step",
        refresh_jti="jti-step-1",
        expires_at=_utcnow() + timedelta(days=7),
    )
    db.add(s)
    db.flush()

    from services.security.security_response_engine import recompute_user_risk_and_enforce

    recompute_user_risk_and_enforce(db, u.id)
    db.refresh(s)
    row = db.query(AuthGlobalRiskScore).filter(AuthGlobalRiskScore.user_id == u.id).first()
    assert row is not None
    assert row.score == 72
    assert s.step_up_otp_required is True


def test_recompute_score_92_revokes_and_blocks_refresh(db, monkeypatch, engine_on):
    monkeypatch.setattr(
        "services.security.security_response_engine.compute_global_risk_score",
        lambda *_a, **_k: (92, "CRITICAL"),
    )
    u = AdminUser(email="tier1_rev@test.dev", hashed_password=get_password_hash("pw"))
    db.add(u)
    db.flush()
    s = AuthSession(
        user_id=u.id,
        device_id="dev-rev",
        refresh_jti="jti-rev-1",
        expires_at=_utcnow() + timedelta(days=7),
    )
    db.add(s)
    db.flush()

    from services.security.security_response_engine import recompute_user_risk_and_enforce

    recompute_user_risk_and_enforce(db, u.id)
    db.refresh(s)
    db.refresh(u)
    assert s.revoked_at is not None
    assert u.security_refresh_blocked is True
    assert u.security_flagged is True


def test_recompute_score_96_locks_account(db, monkeypatch, engine_on):
    monkeypatch.setattr(
        "services.security.security_response_engine.compute_global_risk_score",
        lambda *_a, **_k: (96, "CRITICAL"),
    )
    u = AdminUser(email="tier1_lock@test.dev", hashed_password=get_password_hash("pw"))
    db.add(u)
    db.flush()
    s = AuthSession(
        user_id=u.id,
        device_id="dev-lock",
        refresh_jti="jti-lock-1",
        expires_at=_utcnow() + timedelta(days=7),
    )
    db.add(s)
    db.flush()

    from services.security.security_response_engine import recompute_user_risk_and_enforce

    recompute_user_risk_and_enforce(db, u.id)
    db.refresh(u)
    assert u.security_account_locked_until is not None
    assert u.security_account_locked_until > _utcnow()


def test_enforce_step_up_refresh_required(db, monkeypatch):
    u = AdminUser(email="tier1_enf@test.dev", hashed_password=get_password_hash("pw"))
    db.add(u)
    db.flush()
    db.add(
        AuthSession(
            user_id=u.id,
            device_id="dev-e",
            refresh_jti="jti-e-1",
            expires_at=_utcnow() + timedelta(days=7),
            step_up_otp_required=True,
        )
    )
    db.flush()
    token = create_access_token(data=build_user_jwt_access_base_claims(u))
    with pytest.raises(HTTPException) as ei:
        enforce_access_security(token, u, db)
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "security.step_up_refresh_required"


def test_play_integrity_lenient_rejected_outside_dev(monkeypatch, db):
    monkeypatch.setenv("PLAY_INTEGRITY_USE_GOOGLE_API", "false")
    monkeypatch.setenv("PLAY_INTEGRITY_REQUIRE_API_OUTSIDE_DEV", "true")
    monkeypatch.setattr("core.env.is_dev_mode", lambda: False)
    monkeypatch.setattr(
        "services.auth.device_attestation_service._verify_nonce_optional",
        lambda _db, _nonce: (True, []),
    )
    monkeypatch.setattr(
        "services.auth.device_attestation_service.artifact_replay_seen",
        lambda **kw: False,
    )

    from services.auth.device_attestation_service import _verify_play_integrity

    res = _verify_play_integrity(
        {"integrity_token": "tok", "nonce": "n1", "verdict": {"basicIntegrity": True}},
        "android",
        db,
    )
    assert res.is_valid is False
    assert "play_integrity_api_required_production" in res.risk_flags


def test_apple_attestation_spoof_wrong_challenge(monkeypatch, db):
    monkeypatch.delenv("IOS_ATTEST_APP_ID", raising=False)
    monkeypatch.setattr(
        "services.auth.device_attestation_service._verify_nonce_optional",
        lambda _db, _nonce: (True, []),
    )
    monkeypatch.setattr(
        "services.auth.device_attestation_service.artifact_replay_seen",
        lambda **kw: False,
    )
    inner = json.dumps({"challenge": "not-the-nonce", "type": "webauthn.get"}).encode()
    obj = {
        "authenticatorData": b"\x00" * 37,
        "clientDataJSON": inner,
        "signature": b"\x00" * 64,
    }
    assertion_b64 = base64.b64encode(cbor2.dumps(obj)).decode()
    payload = {
        "format": "apple_app_attest",
        "assertion_b64": assertion_b64,
        "nonce": "expected-server-nonce",
    }
    from services.auth.device_attestation_service import verify_device_attestation

    r = verify_device_attestation("apple_app_attest", payload, "device-x", db=db)
    assert r.is_valid is False
    assert "apple_challenge_nonce_mismatch" in r.risk_flags
