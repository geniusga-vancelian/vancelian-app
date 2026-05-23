"""Inscription e-mail Privy — POST /auth/signup/privy/exchange."""
from __future__ import annotations

import uuid

import pytest
from jose import jwt as jose_jwt
from sqlalchemy import inspect

from auth import ALGORITHM, SECRET_KEY, get_password_hash
from database import AdminUser, Person
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter_between_tests(monkeypatch):
    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "10000")
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture(autouse=True)
def _privy_stub_env(monkeypatch):
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")


@pytest.fixture(autouse=True)
def _require_person_schema(db):
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("admin_users", schema="public")}
    if "person_id" not in cols:
        pytest.skip("Schéma sans admin_users.person_id")


def test_signup_privy_exchange_creates_person_and_session(client, db):
    ext = f"privy-new-{uuid.uuid4().hex[:10]}"
    email = f"new-{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/auth/signup/privy/exchange",
        json={
            "privy_access_token": f"stub:{ext}",
            "email": email,
        },
        headers={"X-Device-ID": "test-signup-privy-device"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("access_token")
    assert body.get("refresh_token")
    claims = jose_jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims.get("sec_inc") is True
    assert claims.get("acct_st") == "PARTIAL"

    u = db.query(AdminUser).filter(AdminUser.email == email).first()
    assert u is not None
    assert u.person_id is not None
    assert u.mobile_e164 is None
    p = db.query(Person).filter(Person.id == u.person_id).first()
    assert p is not None
    collected = (p.profile_json or {}).get("collected") or {}
    assert collected.get("email") == email
    assert collected.get("contact_email") == email


def test_signup_privy_exchange_blocked_existing_email(client, db):
    email = f"exists-{uuid.uuid4().hex[:8]}@example.com"
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
    db.add(
        AdminUser(
            email=email,
            hashed_password=get_password_hash("x"),
            person_id=pid,
        )
    )
    db.commit()

    ext = f"privy-dup-{uuid.uuid4().hex[:10]}"
    res = client.post(
        "/auth/signup/privy/exchange",
        json={"privy_access_token": f"stub:{ext}", "email": email},
    )
    assert res.status_code == 403, res.text
    detail = res.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") in ("signup_email_use_login", "signup_email_unavailable")


def test_signup_privy_exchange_blocked_existing_privy_link(client, db):
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
    ext = f"privy-linked-{uuid.uuid4().hex[:10]}"
    link_external_identity_to_person(
        db,
        person_id=pid,
        provider=PROVIDER_PRIVY,
        external_subject=ext,
    )
    db.commit()

    res = client.post(
        "/auth/signup/privy/exchange",
        json={
            "privy_access_token": f"stub:{ext}",
            "email": f"other-{uuid.uuid4().hex[:8]}@example.com",
        },
    )
    assert res.status_code == 403, res.text


def test_signup_privy_exchange_jwt_uses_body_email_when_access_token_has_no_email(
    client,
    db,
    monkeypatch,
):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from datetime import datetime, timedelta, timezone

    priv_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    app_id = f"privy-signup-app-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "jwt")
    monkeypatch.setenv("PRIVY_APP_ID", app_id)
    monkeypatch.setenv("PRIVY_JWT_VERIFICATION_KEY", pub_pem)

    ext = f"jwt-signup-{uuid.uuid4().hex[:12]}"
    email = f"jwt-signup-{uuid.uuid4().hex[:8]}@example.com"
    claims = {
        "sub": ext,
        "iss": "privy.io",
        "aud": app_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    bearer = jose_jwt.encode(claims, priv_pem, algorithm="ES256")

    res = client.post(
        "/auth/signup/privy/exchange",
        json={"privy_access_token": bearer, "email": email},
        headers={"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    assert db.query(AdminUser).filter(AdminUser.email == email).first() is not None


def test_signup_privy_exchange_ignores_non_evm_wallets_from_jwt(
    client,
    db,
    monkeypatch,
):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from datetime import datetime, timedelta, timezone

    priv_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    app_id = f"privy-signup-app-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "jwt")
    monkeypatch.setenv("PRIVY_APP_ID", app_id)
    monkeypatch.setenv("PRIVY_JWT_VERIFICATION_KEY", pub_pem)

    ext = f"jwt-signup-sol-{uuid.uuid4().hex[:12]}"
    email = f"jwt-signup-sol-{uuid.uuid4().hex[:8]}@example.com"
    claims = {
        "sub": ext,
        "iss": "privy.io",
        "aud": app_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "linked_accounts": [
            {"type": "email", "address": email, "latest_verified_at": 999},
            {
                "type": "wallet",
                "address": "0x" + ("ab" * 20),
                "chain_type": "solana",
                "wallet_client_type": "privy",
            },
        ],
    }
    bearer = jose_jwt.encode(claims, priv_pem, algorithm="ES256")

    res = client.post(
        "/auth/signup/privy/exchange",
        json={"privy_access_token": bearer, "email": email},
        headers={"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    assert db.query(AdminUser).filter(AdminUser.email == email).first() is not None
