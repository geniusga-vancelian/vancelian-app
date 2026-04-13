"""WebAuthn durcissement Phase 3.4 : config stricte, .well-known, OTP admin, diagnostic."""
from __future__ import annotations

from datetime import timedelta

import pytest

from auth import get_password_hash
from database import AdminUser, AuthAdminEmailOtpChallenge, engine, get_db
from services.auth.refresh_session import _utcnow


@pytest.fixture(autouse=True)
def _ensure_auth_admin_email_otp_table():
    """La migration 111 peut ne pas être appliquée sur toutes les DB de test locales."""
    AuthAdminEmailOtpChallenge.__table__.create(bind=engine, checkfirst=True)
    yield


@pytest.fixture(autouse=True)
def _reset_webauthn_cache():
    from services.auth.webauthn_config import reset_webauthn_settings_cache

    reset_webauthn_settings_cache()
    yield
    reset_webauthn_settings_cache()


@pytest.fixture(autouse=True)
def _reset_auth_rate_limit_between_tests():
    from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests

    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


def test_strict_webauthn_rejects_http_origin(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("AUTH_PASSKEYS_ENABLED", "true")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "auth.example.com")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://auth.example.com")
    from services.auth.webauthn_config import (
        load_webauthn_settings_from_env,
        reset_webauthn_settings_cache,
        validate_webauthn_strict,
    )

    reset_webauthn_settings_cache()
    s = load_webauthn_settings_from_env(compute_warnings=False)
    with pytest.raises(RuntimeError) as ei:
        validate_webauthn_strict(s)
    assert "https" in str(ei.value).lower()


def test_strict_webauthn_rejects_rp_host_mismatch(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_PASSKEYS_ENABLED", "true")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "auth.example.com")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "https://other.com")
    from services.auth.webauthn_config import (
        load_webauthn_settings_from_env,
        reset_webauthn_settings_cache,
        validate_webauthn_strict,
    )

    reset_webauthn_settings_cache()
    s = load_webauthn_settings_from_env(compute_warnings=False)
    with pytest.raises(RuntimeError) as ei:
        validate_webauthn_strict(s)
    assert "WEBAUTHN_RP_ID" in str(ei.value) or "match" in str(ei.value).lower()


def test_well_known_aasa_and_assetlinks_json(client, monkeypatch):
    monkeypatch.setenv("WEBAUTHN_AASA_APP_IDS", "ABCDE.com.example.app")
    monkeypatch.setenv("ANDROID_PACKAGE_NAME", "com.example.app")
    monkeypatch.setenv("ANDROID_SHA256_CERT_FINGERPRINTS", "AA:BB")
    r = client.get("/.well-known/apple-app-site-association")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    j = r.json()
    assert "webcredentials" in j
    assert j["webcredentials"]["apps"] == ["ABCDE.com.example.app"]

    r2 = client.get("/apple-app-site-association")
    assert r2.status_code == 200
    assert r2.json()["webcredentials"]["apps"] == ["ABCDE.com.example.app"]

    r3 = client.get("/.well-known/assetlinks.json")
    assert r3.status_code == 200
    assert r3.headers.get("content-type", "").startswith("application/json")
    al = r3.json()
    assert isinstance(al, list)
    assert al[0]["target"]["package_name"] == "com.example.app"


def test_admin_passkeys_config_requires_auth(client, db):
    r = client.get("/admin/security/passkeys/config")
    assert r.status_code == 401


def test_admin_passkeys_config_ok(client, db):
    from tests.conftest import make_admin_headers

    h = make_admin_headers(db)
    r = client.get("/admin/security/passkeys/config", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert "rp_id" in body and "origins" in body
    assert "warnings" in body


def test_admin_email_otp_disabled_returns_503(test_app, client, db, monkeypatch):
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "false")

    def _override_get_db():
        yield db

    test_app.dependency_overrides[get_db] = _override_get_db
    try:
        db.add(AdminUser(email="otp@example.com", hashed_password=get_password_hash("pw")))
        db.commit()
        r = client.post("/auth/login/email-otp/start", json={"email": "otp@example.com"})
        assert r.status_code == 503
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_admin_email_otp_happy_path(test_app, client, db, monkeypatch):
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    from services.auth import admin_email_otp_routes

    class _FakeMail:
        is_noop = False
        sent = None

        def send_otp(self, to_email: str, code: str) -> None:
            self.sent = (to_email, code)

    fake = _FakeMail()
    monkeypatch.setattr(admin_email_otp_routes, "get_email_provider", lambda: fake)

    def _override_get_db():
        yield db

    test_app.dependency_overrides[get_db] = _override_get_db
    try:
        db.add(AdminUser(email="happy@example.com", hashed_password=get_password_hash("pw")))
        db.commit()
        st = client.post("/auth/login/email-otp/start", json={"email": "happy@example.com"})
        assert st.status_code == 200, st.text
        assert fake.sent is not None
        code = fake.sent[1]
        vf = client.post(
            "/auth/login/email-otp/verify",
            json={"email": "happy@example.com", "code": code},
            headers={"X-Device-ID": "dev-otp"},
        )
        assert vf.status_code == 200, vf.text
        assert vf.json().get("access_token")
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_admin_email_otp_verify_forbidden_when_security_account_locked(test_app, client, db, monkeypatch):
    """Parité avec login SMS OTP : pas de session si security_account_locked_until actif."""
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    from services.auth import admin_email_otp_routes

    class _FakeMail:
        is_noop = False
        sent = None

        def send_otp(self, to_email: str, code: str) -> None:
            self.sent = (to_email, code)

    fake = _FakeMail()
    monkeypatch.setattr(admin_email_otp_routes, "get_email_provider", lambda: fake)

    def _override_get_db():
        yield db

    test_app.dependency_overrides[get_db] = _override_get_db
    try:
        db.add(
            AdminUser(
                email="locked-otp@example.com",
                hashed_password=get_password_hash("pw"),
                security_account_locked_until=_utcnow() + timedelta(hours=24),
            )
        )
        db.commit()
        st = client.post("/auth/login/email-otp/start", json={"email": "locked-otp@example.com"})
        assert st.status_code == 200, st.text
        code = fake.sent[1]
        vf = client.post(
            "/auth/login/email-otp/verify",
            json={"email": "locked-otp@example.com", "code": code},
            headers={"X-Device-ID": "dev-locked"},
        )
        assert vf.status_code == 403, vf.text
        detail = vf.json().get("detail")
        assert isinstance(detail, dict)
        assert detail.get("code") == "security.account_locked"
        row = (
            db.query(AuthAdminEmailOtpChallenge)
            .filter(AuthAdminEmailOtpChallenge.email_normalized == "locked-otp@example.com")
            .first()
        )
        assert row is not None
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_two_factor_purpose_login_still_allowed():
    from services.security.two_factor_purposes import validate_purpose
    from services.security.two_factor_exceptions import TwoFactorException

    validate_purpose("login", relaxed=False)
    with pytest.raises(TwoFactorException) as ei:
        validate_purpose("not_a_real_purpose_ever", relaxed=False)
    assert ei.value.code == "purpose_not_allowed"
