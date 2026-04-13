"""Tests connexion admin OTP SMS — alignés sur sms_otp_core + provider SMS (fake en test)."""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import inspect

from auth import get_password_hash
from database import AdminUser, AuthMobileLoginOtpChallenge
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests
from services.auth.refresh_session import _utcnow


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter_between_tests():
    """Le middleware /auth/* partage un limiteur mémoire singleton — sans reset, les tests se bloquent en 429."""
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture(autouse=True)
def _require_admin_mobile_column(db):
    """Nécessite la migration ``117_admin_mobile_login_otp`` (colonne ``admin_users.mobile_e164``)."""
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("admin_users", schema="public")}
    if "mobile_e164" not in cols:
        pytest.skip("Schéma sans admin_users.mobile_e164 — exécuter alembic upgrade head")


@pytest.fixture(autouse=True)
def _mobile_otp_env(monkeypatch):
    monkeypatch.setenv("AUTH_MOBILE_OTP_LOGIN_ENABLED", "true")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "123456")


def test_sms_start_creates_challenge_and_verify_issues_tokens(client, db):
    phone = "+33699112233"
    email = f"sms-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()

    r = client.post("/auth/login/sms/start", json={"phone": phone})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "accepted"
    assert body.get("resend_after_seconds") == 30
    assert "masked_target" in body
    assert body.get("sms_otp_dispatched") is True

    row = (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
    )
    assert row is not None

    r2 = client.post(
        "/auth/login/sms/verify",
        json={"phone": phone, "code": "123456"},
        headers={"X-Device-ID": "test-device-otp"},
    )
    assert r2.status_code == 200, r2.text
    assert "access_token" in r2.json()
    assert (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
        is None
    )


def test_legacy_login_paths_alias(client, db):
    phone = "+33699223344"
    email = f"leg-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()

    r = client.post("/auth/login/start", json={"phone": phone})
    assert r.status_code == 200, r.text
    r2 = client.post(
        "/auth/login/verify",
        json={"phone": phone, "code": "123456"},
        headers={"X-Device-ID": "test-legacy"},
    )
    assert r2.status_code == 200, r2.text
    assert "access_token" in r2.json()


def test_unknown_phone_no_persisted_challenge(client, db):
    phone = "+33600000999"
    r = client.post("/auth/login/sms/start", json={"phone": phone})
    assert r.status_code == 200, r.text
    assert r.json().get("sms_otp_dispatched") is False
    assert (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
        is None
    )


def test_verify_wrong_code_401(client, db):
    phone = "+33688334455"
    email = f"bad-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()
    client.post("/auth/login/sms/start", json={"phone": phone})
    r = client.post(
        "/auth/login/sms/verify",
        json={"phone": phone, "code": "000000"},
        headers={"X-Device-ID": "d1"},
    )
    assert r.status_code == 401
    detail = r.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "invalid_or_expired_code"


def test_resend_rate_limited(client, db):
    phone = "+33677445566"
    email = f"rs-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()
    r1 = client.post("/auth/login/sms/start", json={"phone": phone})
    assert r1.status_code == 200
    r2 = client.post("/auth/login/sms/start", json={"phone": phone})
    assert r2.status_code == 429
    detail = r2.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "resend_rate_limited"


def test_expired_challenge_rejected(client, db):
    phone = "+33666554433"
    email = f"ex-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()
    client.post("/auth/login/sms/start", json={"phone": phone})
    row = (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
    )
    assert row is not None
    row.expires_at = _utcnow() - timedelta(minutes=1)
    db.flush()

    r = client.post(
        "/auth/login/sms/verify",
        json={"phone": phone, "code": "123456"},
        headers={"X-Device-ID": "d2"},
    )
    assert r.status_code == 401


def test_feature_disabled_503(client, db, monkeypatch):
    monkeypatch.setenv("AUTH_MOBILE_OTP_LOGIN_ENABLED", "false")
    r = client.post("/auth/login/sms/start", json={"phone": "+33611112222"})
    assert r.status_code == 503


def test_verify_forbidden_when_security_account_locked(client, db):
    """Alignement sur perform_login : compte verrouillé ne doit pas recevoir de session même avec OTP valide."""
    phone = "+33655443322"
    email = f"lck-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    u.security_account_locked_until = _utcnow() + timedelta(hours=24)
    db.add(u)
    db.flush()

    r1 = client.post("/auth/login/sms/start", json={"phone": phone})
    assert r1.status_code == 200, r1.text

    r2 = client.post(
        "/auth/login/sms/verify",
        json={"phone": phone, "code": "123456"},
        headers={"X-Device-ID": "test-device-locked"},
    )
    assert r2.status_code == 403, r2.text
    detail = r2.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "security.account_locked"
    # Le challenge ne doit pas être consommé (réutilisable après levée du verrou).
    assert (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
        is not None
    )


def test_apply_auth_mobile_otp_start_min_latency_sleeps_delta(monkeypatch):
    """Mitigation timing : `_apply_*` complète jusqu’à AUTH_MOBILE_OTP_START_MIN_LATENCY_MS."""
    import services.auth.mobile_otp_login_routes as m

    monkeypatch.setenv("AUTH_MOBILE_OTP_START_MIN_LATENCY_MS", "250")
    sleeps: list[float] = []
    monkeypatch.setattr(m.time, "sleep", lambda s: sleeps.append(float(s)))
    monkeypatch.setattr(m.time, "perf_counter", lambda: 1000.05)

    m._apply_auth_mobile_otp_start_min_latency(1000.0)
    assert len(sleeps) == 1
    assert 0.19 <= sleeps[0] <= 0.21


def test_apply_auth_mobile_otp_start_min_latency_noop_when_unset(monkeypatch):
    import services.auth.mobile_otp_login_routes as m

    monkeypatch.delenv("AUTH_MOBILE_OTP_START_MIN_LATENCY_MS", raising=False)
    sleeps: list[float] = []
    monkeypatch.setattr(m.time, "sleep", lambda s: sleeps.append(s))
    m._apply_auth_mobile_otp_start_min_latency(0.0)
    assert sleeps == []


def test_apply_auth_mobile_otp_start_min_latency_no_sleep_if_already_slow(monkeypatch):
    import services.auth.mobile_otp_login_routes as m

    monkeypatch.setenv("AUTH_MOBILE_OTP_START_MIN_LATENCY_MS", "100")
    sleeps: list[float] = []
    monkeypatch.setattr(m.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(m.time, "perf_counter", lambda: 1000.2)

    m._apply_auth_mobile_otp_start_min_latency(1000.0)
    assert sleeps == []


def test_resend_supersedes_challenge_old_code_rejected(client, db, monkeypatch):
    """Deuxième start après fenêtre resend : nouveau hash ; l’ancien code ne doit plus valider."""
    import services.auth.mobile_otp_login_routes as routes

    monkeypatch.setattr(routes, "RESEND_SECONDS", 0)
    seq = iter(["111111", "222222"])
    monkeypatch.setattr(routes, "new_plaintext_sms_otp", lambda: next(seq))

    phone = "+33611223399"
    email = f"rs2-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), mobile_e164=phone)
    db.add(u)
    db.flush()

    assert client.post("/auth/login/sms/start", json={"phone": phone}).status_code == 200
    assert client.post("/auth/login/sms/start", json={"phone": phone}).status_code == 200

    r_bad = client.post(
        "/auth/login/sms/verify",
        json={"phone": phone, "code": "111111"},
        headers={"X-Device-ID": "d-super"},
    )
    assert r_bad.status_code == 401

    r_ok = client.post(
        "/auth/login/sms/verify",
        json={"phone": phone, "code": "222222"},
        headers={"X-Device-ID": "d-super"},
    )
    assert r_ok.status_code == 200, r_ok.text
