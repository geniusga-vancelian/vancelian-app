"""PR2 : émission JWT avec ``sub`` = ``admin_users.id`` et ``sub_typ`` = ``user_id``."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from jose import jwt

from auth import ALGORITHM, SECRET_KEY, create_registration_otp_token
from auth import get_password_hash
from database import AdminUser
from conftest import make_admin_user_with_pe_client
from services.auth.jwt_user_claims import (
    format_user_jwt_sub,
    get_jwt_emission_metrics,
    reset_jwt_emission_metrics,
)
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests


@pytest.fixture(autouse=True)
def _auth_rl_high(monkeypatch):
    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REFRESH_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REVOKE_MAX", "10000")
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture
def client_main_app_db(db):
    from main import app
    from database import get_db

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


_HDR = {"X-Device-ID": "legacy-unknown"}


@pytest.fixture(autouse=True)
def _reset_emission_metrics():
    reset_jwt_emission_metrics()
    yield
    reset_jwt_emission_metrics()


def test_emission_metric_increments_on_login(client_main_app_db, db):
    reset_jwt_emission_metrics()
    email = f"pr2-metric-{uuid.uuid4().hex[:8]}@example.com"
    make_admin_user_with_pe_client(db, email=email, password="metric-PW-1!")
    db.commit()
    before = get_jwt_emission_metrics()["jwt_user_tokens_emitted_count"]
    r = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "metric-PW-1!"},
        headers=_HDR,
    )
    assert r.status_code == 200
    after = get_jwt_emission_metrics()["jwt_user_tokens_emitted_count"]
    assert after >= before + 1


def test_login_emits_access_sub_user_id_and_sub_typ(client_main_app_db, db):
    email = f"pr2-login-{uuid.uuid4().hex[:8]}@example.com"
    make_admin_user_with_pe_client(db, email=email, password="secret-PW-99!")
    db.commit()

    r = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "secret-PW-99!"},
        headers=_HDR,
    )
    assert r.status_code == 200
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    assert user is not None

    at = r.json()["access_token"]
    pl = jwt.decode(at, SECRET_KEY, algorithms=[ALGORITHM])
    assert pl["sub"] == format_user_jwt_sub(user.id)
    assert pl["sub_typ"] == "user_id"
    if user.person_id is not None:
        assert pl.get("person_id") == str(user.person_id)
        assert "pid" not in pl

    rt = r.json()["refresh_token"]
    rp = jwt.decode(rt, SECRET_KEY, algorithms=[ALGORITHM])
    assert rp["sub"] == format_user_jwt_sub(user.id)
    assert rp.get("sub_typ") == "user_id"
    assert rp.get("typ") == "refresh"


def test_refresh_from_new_refresh_reissues_user_id_claims(client_main_app_db, db):
    email = f"pr2-refresh-{uuid.uuid4().hex[:8]}@example.com"
    make_admin_user_with_pe_client(db, email=email, password="x")
    db.commit()

    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "x"},
        headers=_HDR,
    )
    assert login.status_code == 200
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    rt1 = login.json()["refresh_token"]

    r2 = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt1}, headers=_HDR)
    assert r2.status_code == 200
    at2 = r2.json()["access_token"]
    rt2 = r2.json()["refresh_token"]
    pl_a = jwt.decode(at2, SECRET_KEY, algorithms=[ALGORITHM])
    assert pl_a["sub"] == format_user_jwt_sub(user.id)
    assert pl_a["sub_typ"] == "user_id"
    pl_r = jwt.decode(rt2, SECRET_KEY, algorithms=[ALGORITHM])
    assert pl_r["sub"] == format_user_jwt_sub(user.id)
    assert pl_r.get("sub_typ") == "user_id"


def test_legacy_email_refresh_token_is_rejected(client_main_app_db, db):
    """Les refresh dont ``sub`` est un e-mail ne sont plus acceptés (``sub`` = ``au:<id>`` uniquement)."""
    email = f"pr2-legacy-{uuid.uuid4().hex[:8]}@example.com"
    make_admin_user_with_pe_client(db, email=email, password="y")
    db.commit()

    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + timedelta(days=14)
    legacy_rt = jwt.encode(
        {
            "sub": email,
            "exp": expire,
            "typ": "refresh",
            "jti": jti,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    r = client_main_app_db.post("/auth/refresh", json={"refresh_token": legacy_rt}, headers=_HDR)
    assert r.status_code == 401


def test_registration_otp_token_unchanged():
    tok = create_registration_otp_token(uuid.uuid4())
    pl = jwt.decode(tok, SECRET_KEY, algorithms=[ALGORITHM])
    assert pl.get("sub") == "registration:2fa"
    assert "sub_typ" not in pl or pl.get("sub_typ") != "user_id"
