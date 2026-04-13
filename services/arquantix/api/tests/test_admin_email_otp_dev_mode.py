"""Mode dev e-mail OTP : aligné sur SMS (TWO_FACTOR_DEV_FIXED_CODE, noop SES, dev_code JSON)."""

from __future__ import annotations

import pytest

from auth import get_password_hash
from database import AdminUser, AuthAdminEmailOtpChallenge, engine, get_db


@pytest.fixture(autouse=True)
def _ensure_auth_admin_email_otp_table():
    AuthAdminEmailOtpChallenge.__table__.create(bind=engine, checkfirst=True)
    yield


@pytest.fixture(autouse=True)
def _reset_auth_rate_limit_between_tests():
    from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests

    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture
def _admin_user(db):
    u = AdminUser(email="dev-otp@example.com", hashed_password=get_password_hash("pw"))
    db.add(u)
    db.commit()
    return u


def _with_db(test_app, db):
    def _override_get_db():
        yield db

    test_app.dependency_overrides[get_db] = _override_get_db


def test_email_otp_dev_fixed_code(test_app, client, db, monkeypatch, _admin_user):
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    monkeypatch.delenv("TWO_FACTOR_DEV_EXPOSE_CODE", raising=False)
    from services.auth import admin_email_otp_routes

    class _FakeMail:
        is_noop = False
        sent = None

        def send_otp(self, to_email: str, code: str) -> None:
            self.sent = (to_email, code)

    fake = _FakeMail()
    monkeypatch.setattr(admin_email_otp_routes, "get_email_provider", lambda: fake)
    _with_db(test_app, db)
    try:
        st = client.post("/auth/login/email-otp/start", json={"email": "dev-otp@example.com"})
        assert st.status_code == 200, st.text
        assert fake.sent is not None
        assert fake.sent[1] == "111111"
        vf = client.post(
            "/auth/login/email-otp/verify",
            json={"email": "dev-otp@example.com", "code": "111111"},
            headers={"X-Device-ID": "dev-otp-fixed"},
        )
        assert vf.status_code == 200, vf.text
        assert vf.json().get("access_token")
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_email_otp_dev_noop_provider(test_app, client, db, monkeypatch, _admin_user):
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SES_FROM_EMAIL", raising=False)
    monkeypatch.delenv("AWS_SES_FROM", raising=False)
    _with_db(test_app, db)
    try:
        st = client.post("/auth/login/email-otp/start", json={"email": "dev-otp@example.com"})
        assert st.status_code == 200, st.text
        body = st.json()
        assert body.get("status") == "accepted"
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_email_otp_accepts_local_domain_email(test_app, client, db, monkeypatch):
    """Les adresses ``*.local`` sont refusées par ``EmailStr`` ; le login admin doit les accepter."""
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    u = AdminUser(email="user@test.arquantix.local", hashed_password=get_password_hash("pw"))
    db.add(u)
    db.commit()
    from services.auth import admin_email_otp_routes

    class _FakeMail:
        is_noop = False

        def send_otp(self, to_email: str, code: str) -> None:
            pass

    monkeypatch.setattr(admin_email_otp_routes, "get_email_provider", lambda: _FakeMail())
    _with_db(test_app, db)
    try:
        st = client.post(
            "/auth/login/email-otp/start",
            json={"email": "user@test.arquantix.local"},
        )
        assert st.status_code == 200, st.text
        assert st.json().get("status") == "accepted"
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_email_otp_dev_expose_code(test_app, client, db, monkeypatch, _admin_user):
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    monkeypatch.setenv("TWO_FACTOR_DEV_EXPOSE_CODE", "true")
    from services.auth import admin_email_otp_routes

    class _FakeMail:
        is_noop = False

        def send_otp(self, to_email: str, code: str) -> None:
            pass

    monkeypatch.setattr(admin_email_otp_routes, "get_email_provider", lambda: _FakeMail())
    _with_db(test_app, db)
    try:
        st = client.post("/auth/login/email-otp/start", json={"email": "dev-otp@example.com"})
        assert st.status_code == 200, st.text
        assert st.json().get("dev_code") == "111111"
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_email_otp_prod_mode_noop_returns_503(test_app, client, db, monkeypatch, _admin_user):
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SES_FROM_EMAIL", raising=False)
    monkeypatch.delenv("AWS_SES_FROM", raising=False)
    _with_db(test_app, db)
    try:
        st = client.post("/auth/login/email-otp/start", json={"email": "dev-otp@example.com"})
        assert st.status_code == 503, st.text
    finally:
        test_app.dependency_overrides.pop(get_db, None)


def test_email_otp_prod_mode_no_dev_code_in_json(test_app, client, db, monkeypatch, _admin_user):
    monkeypatch.setenv("AUTH_ADMIN_EMAIL_OTP_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TWO_FACTOR_DEV_EXPOSE_CODE", "true")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    from services.auth import admin_email_otp_routes

    class _FakeMail:
        is_noop = False

        def send_otp(self, to_email: str, code: str) -> None:
            pass

    monkeypatch.setattr(admin_email_otp_routes, "get_email_provider", lambda: _FakeMail())
    _with_db(test_app, db)
    try:
        st = client.post("/auth/login/email-otp/start", json={"email": "dev-otp@example.com"})
        assert st.status_code == 200, st.text
        assert st.json().get("dev_code") is None
        assert len(st.json().get("status")) > 0
    finally:
        test_app.dependency_overrides.pop(get_db, None)
