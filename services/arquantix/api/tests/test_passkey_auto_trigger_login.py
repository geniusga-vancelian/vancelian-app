"""Recommandation passkey auto (SMS start) + éligibilité + endpoint /prompt analytics."""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import inspect

from auth import get_password_hash
from database import AdminUser, AuthPasskey, AuthMobileLoginOtpChallenge, AuthUserDeviceProfile
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests
from services.auth.refresh_session import _utcnow
from services.security.device_reputation.device_identity import build_device_hash


@pytest.fixture(autouse=True)
def _reset_rl():
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture(autouse=True)
def _schema(db):
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("admin_users", schema="public")}
    if "mobile_e164" not in cols:
        pytest.skip("admin_users.mobile_e164 manquant — alembic upgrade head")
    tables = insp.get_table_names(schema="public")
    if "auth_user_device_profiles" not in tables:
        pytest.skip("auth_user_device_profiles manquant — alembic upgrade head")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("AUTH_MOBILE_OTP_LOGIN_ENABLED", "true")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "123456")
    monkeypatch.setenv("LOGIN_AUTH_STRATEGY_ENABLED", "true")
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "true")
    monkeypatch.setenv("PASSKEY_AUTO_TRIGGER_ENABLED", "true")
    monkeypatch.setenv("PASSKEY_AUTO_EXPOSE_LOGIN_EMAIL", "true")
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "false")


def _add_passkey(db, user_id: int) -> None:
    db.add(
        AuthPasskey(
            id=uuid.uuid4(),
            user_id=user_id,
            credential_id_b64="dGVzdGNpZA",
            public_key_b64="dGVzdGtleQ",
            sign_count=1,
        )
    )


def test_sms_start_recommends_passkey_trusted_device(client, db, monkeypatch):
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_RP_NAME", "Test")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://localhost")

    phone = "+33688112299"
    email = f"pkauto-{uuid.uuid4().hex[:8]}@example.com"
    dev_id = "device-trusted-pk"
    dh = build_device_hash(dev_id, None, None)

    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()
    _add_passkey(db, u.id)
    now = _utcnow()
    db.add(
        AuthUserDeviceProfile(
            id=uuid.uuid4(),
            user_id=u.id,
            device_hash=dh,
            device_id=dev_id,
            fingerprint_hash=None,
            first_seen_at=now - timedelta(days=25),
            last_seen_at=now,
            login_count=30,
            successful_login_count=28,
            failed_login_count=1,
            trust_score=85,
            trust_level="HIGH",
        )
    )
    db.flush()

    r = client.post(
        "/auth/login/sms/start",
        json={"phone": phone},
        headers={"X-Device-ID": dev_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("recommended_auth_method") == "passkey"
    assert body.get("fallback_auth_method") == "otp"
    assert body.get("passkey_auto_eligible") is True
    assert body.get("passkey_login_email") == email
    assert body.get("device_trust_level") == "HIGH"


def test_sms_start_recommends_otp_untrusted_device(client, db, monkeypatch):
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_RP_NAME", "Test")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://localhost")

    phone = "+33688112300"
    email = f"pklow-{uuid.uuid4().hex[:8]}@example.com"
    dev_id = "device-new-pk"
    dh = build_device_hash(dev_id, None, None)

    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()
    _add_passkey(db, u.id)
    now = _utcnow()
    db.add(
        AuthUserDeviceProfile(
            id=uuid.uuid4(),
            user_id=u.id,
            device_hash=dh,
            device_id=dev_id,
            first_seen_at=now,
            last_seen_at=now,
            login_count=1,
            successful_login_count=1,
            failed_login_count=0,
            trust_score=20,
            trust_level="LOW",
        )
    )
    db.flush()

    r = client.post(
        "/auth/login/sms/start",
        json={"phone": phone},
        headers={"X-Device-ID": dev_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("recommended_auth_method") == "otp"
    assert body.get("passkey_login_email") in (None, "")


def test_sms_start_recommends_otp_without_passkey(client, db):
    phone = "+33688112301"
    email = f"nopk-{uuid.uuid4().hex[:8]}@example.com"
    dev_id = "device-no-pk"
    dh = build_device_hash(dev_id, None, None)

    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()
    now = _utcnow()
    db.add(
        AuthUserDeviceProfile(
            id=uuid.uuid4(),
            user_id=u.id,
            device_hash=dh,
            device_id=dev_id,
            first_seen_at=now - timedelta(days=30),
            last_seen_at=now,
            login_count=50,
            successful_login_count=50,
            failed_login_count=0,
            trust_score=90,
            trust_level="HIGH",
        )
    )
    db.flush()

    r = client.post(
        "/auth/login/sms/start",
        json={"phone": phone},
        headers={"X-Device-ID": dev_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("recommended_auth_method") == "otp"
    assert body.get("passkey_auto_eligible") is False


def test_passkey_prompt_accepts_auto_trigger_events(client):
    r = client.post(
        "/auth/passkeys/prompt",
        json={
            "event": "auth.login.passkey_auto_triggered",
            "identifier_domain": "example.com",
            "detail": "unit",
        },
    )
    assert r.status_code == 204, r.text


def test_evaluate_passkey_login_eligibility_unit(db, monkeypatch):
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    from services.auth.passkey_login_eligibility import evaluate_passkey_login_eligibility

    email = f"elu-{uuid.uuid4().hex[:8]}@t.dev"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()
    _add_passkey(db, u.id)
    db.flush()

    risk_ok = {
        "decision_hint": "otp_only",
        "device_trust_level": "HIGH",
        "login_risk_score": 30,
        "global_risk_level": "LOW",
        "signals": [],
    }
    out = evaluate_passkey_login_eligibility(
        db,
        u,
        device_context={"device_id": "x"},
        risk_context=risk_ok,
        step_up_required=False,
    )
    assert out.recommended is True

    risk_bad = dict(risk_ok)
    risk_bad["device_trust_level"] = "LOW"
    out2 = evaluate_passkey_login_eligibility(
        db,
        u,
        device_context={},
        risk_context=risk_bad,
        step_up_required=False,
    )
    assert out2.recommended is False
