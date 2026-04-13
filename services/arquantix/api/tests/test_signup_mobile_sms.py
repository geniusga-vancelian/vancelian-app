"""Inscription mobile SMS — /auth/signup/sms/* (Person + AdminUser + session)."""
from __future__ import annotations

import uuid

import pytest
from jose import jwt as jose_jwt
from sqlalchemy import inspect

from auth import ALGORITHM, SECRET_KEY, get_password_hash
from database import AdminUser, AuthMobileLoginOtpChallenge, Person
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter_between_tests(monkeypatch):
    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "10000")
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture(autouse=True)
def _require_admin_mobile_and_person(db):
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("admin_users", schema="public")}
    if "mobile_e164" not in cols or "person_id" not in cols:
        pytest.skip("Schéma sans admin_users.mobile_e164 / person_id — alembic upgrade head")


@pytest.fixture(autouse=True)
def _mobile_otp_env(monkeypatch):
    monkeypatch.setenv("AUTH_MOBILE_OTP_LOGIN_ENABLED", "true")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "123456")


def test_signup_start_sends_challenge_and_verify_creates_user_with_person(client, db):
    phone = "+33699112299"
    r = client.post("/auth/signup/sms/start", json={"phone": phone})
    assert r.status_code == 200, r.text
    row = (
        db.query(AuthMobileLoginOtpChallenge)
        .filter(AuthMobileLoginOtpChallenge.phone_e164_normalized == phone)
        .first()
    )
    assert row is not None

    r2 = client.post(
        "/auth/signup/sms/verify",
        json={"phone": phone, "code": "123456"},
        headers={"X-Device-ID": "test-signup-device"},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert "access_token" in body
    assert "refresh_token" in body
    claims = jose_jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims.get("sec_inc") is True
    assert claims.get("acct_st") == "PARTIAL"

    u = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
    assert u is not None
    assert u.person_id is not None
    p = db.query(Person).filter(Person.id == u.person_id).first()
    assert p is not None
    assert (p.jurisdiction or "").upper() == "EU"
    collected = (p.profile_json or {}).get("collected") or {}
    assert collected.get("phone_e164") == phone


def test_signup_start_blocked_partial_account_signup_phone_use_login(client, db):
    """Compte PARTIAL (Person sans ACK / sans PeClient) : inscription refusée, code explicite."""
    phone = "+33688112299"
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    pid = uuid.uuid4()
    person = Person(
        id=pid,
        status="active",
        jurisdiction="EU",
        profile_json={"collected": {}, "computed": {}, "compliance": {}},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    u = AdminUser(
        email=email,
        hashed_password=get_password_hash("x"),
        mobile_e164=phone,
        person_id=pid,
    )
    db.add(u)
    db.flush()

    r = client.post("/auth/signup/sms/start", json={"phone": phone})
    assert r.status_code == 403, r.text
    detail = r.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "signup_phone_use_login"
    assert detail.get("account_state") == "PARTIAL"


def test_signup_start_blocked_when_active_portfolio_exists(client, db):
    """Compte ACTIVE (ACK + PeClient) : inscription refusée classique."""
    from conftest import make_linked_client

    phone = "+33688112200"
    pe = make_linked_client(db, email=f"cli-{uuid.uuid4().hex[:6]}@portfolio.test")
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(
        email=email,
        hashed_password=get_password_hash("x"),
        mobile_e164=phone,
        person_id=pe.person_id,
    )
    db.add(u)
    db.flush()

    r = client.post("/auth/signup/sms/start", json={"phone": phone})
    assert r.status_code == 403, r.text
    detail = r.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "signup_phone_unavailable"
    assert detail.get("account_state") == "ACTIVE"


def test_signup_start_ok_when_only_web_only_admin_holds_phone(client, db):
    """Pas de Person / pe_clients : un admin web-only avec mobile ne doit pas bloquer le 1er client app."""
    phone = "+33655112299"
    u = AdminUser(
        email=f"webonly-{uuid.uuid4().hex[:8]}@internal.test",
        hashed_password=get_password_hash("x"),
        mobile_e164=phone,
        mobile_app_allowed=False,
        person_id=None,
    )
    db.add(u)
    db.flush()

    r = client.post("/auth/signup/sms/start", json={"phone": phone})
    assert r.status_code == 200, r.text


def test_signup_start_ok_when_orphan_admin_without_person(client, db):
    """Orphelin : mobile sur admin_users sans person_id — ne bloque plus l'inscription (start)."""
    phone = "+33644112233"
    u = AdminUser(
        email=f"orph-{uuid.uuid4().hex[:8]}@internal.test",
        hashed_password=get_password_hash("x"),
        mobile_e164=phone,
        person_id=None,
        mobile_app_allowed=True,
    )
    db.add(u)
    db.flush()

    r = client.post("/auth/signup/sms/start", json={"phone": phone})
    assert r.status_code == 200, r.text


def test_signup_verify_reuses_person_when_profile_has_phone_only(client, db):
    """Résiduel persons.profile_json.collected.phone_e164 sans AdminUser : rattacher, pas doublon Person."""
    phone = "+33677112288"
    pid = uuid.uuid4()
    person = Person(
        id=pid,
        status="active",
        jurisdiction="EU",
        profile_json={
            "collected": {"phone_e164": phone},
            "computed": {},
            "compliance": {},
        },
        kyc_status="not_started",
    )
    db.add(person)
    db.commit()

    r = client.post("/auth/signup/sms/start", json={"phone": phone})
    assert r.status_code == 200, r.text
    r2 = client.post(
        "/auth/signup/sms/verify",
        json={"phone": phone, "code": "123456"},
        headers={"X-Device-ID": "test-signup-reuse-person"},
    )
    assert r2.status_code == 200, r2.text
    u = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
    assert u is not None
    assert u.person_id == pid
