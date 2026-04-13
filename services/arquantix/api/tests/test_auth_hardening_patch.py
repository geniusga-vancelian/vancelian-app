"""Durcissement Phase 2 patch : revoke + device, rate limits, cleanup JTI."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from database import AuthSpentRefreshJti, get_db
from conftest import make_admin_user_with_pe_client
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests
from services.auth.spent_jti_cleanup import run_spent_jti_cleanup


@pytest.fixture
def client_main_app_db(db):
    from main import app

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _reset_rl_singleton(monkeypatch):
    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REFRESH_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REVOKE_MAX", "10000")
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


def test_revoke_succeeds_without_header_when_jwt_carries_device(client_main_app_db, db):
    """PR B : sans ``X-Device-ID``, l’appareil effectif vient du JWT (ex. ``srvtmp-*`` émis au login)."""
    email = "revoke_hdr@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    assert login.status_code == 200
    rt = login.json()["refresh_token"]
    r = client_main_app_db.post("/auth/revoke", json={"refresh_token": rt})
    assert r.status_code == 204


def test_revoke_rejects_wrong_device(client_main_app_db, db):
    email = "revoke_dev@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "p"},
        headers={"X-Device-ID": "good-phone"},
    )
    rt = login.json()["refresh_token"]
    bad = client_main_app_db.post(
        "/auth/revoke",
        json={"refresh_token": rt},
        headers={"X-Device-ID": "other-phone"},
    )
    assert bad.status_code == 401


def test_login_rate_limited_after_quota(client_main_app_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "2")
    reset_auth_rate_limiter_for_tests()
    email = "rl_login@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    for _ in range(2):
        r = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
        assert r.status_code == 200
    r3 = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    assert r3.status_code == 429
    body = r3.json()
    assert body.get("error", {}).get("code") == "rate_limited"


def test_refresh_rate_limited_per_device(client_main_app_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_RL_REFRESH_MAX", "2")
    reset_auth_rate_limiter_for_tests()
    email = "rl_ref@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    hdr = {"X-Device-ID": "refresh-rl-device"}
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "p"},
        headers=hdr,
    )
    rt = login.json()["refresh_token"]
    a = client_main_app_db.post(
        "/auth/refresh",
        json={"refresh_token": rt},
        headers=hdr,
    )
    assert a.status_code == 200
    rt2 = a.json()["refresh_token"]
    b = client_main_app_db.post(
        "/auth/refresh",
        json={"refresh_token": rt2},
        headers=hdr,
    )
    assert b.status_code == 200
    rt3 = b.json()["refresh_token"]
    c = client_main_app_db.post(
        "/auth/refresh",
        json={"refresh_token": rt3},
        headers=hdr,
    )
    assert c.status_code == 429


def test_revoke_rate_limited_per_device(client_main_app_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_RL_REVOKE_MAX", "2")
    reset_auth_rate_limiter_for_tests()
    hdr = {"X-Device-ID": "revoke-rl-device"}
    email = "rl_rvk@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()

    def _login_rt():
        lo = client_main_app_db.post(
            "/auth/login",
            json={"email": email, "password": "p"},
            headers=hdr,
        )
        assert lo.status_code == 200
        return lo.json()["refresh_token"]

    for _ in range(2):
        rt = _login_rt()
        rv = client_main_app_db.post(
            "/auth/revoke",
            json={"refresh_token": rt},
            headers=hdr,
        )
        assert rv.status_code == 204
    rt3 = _login_rt()
    r3 = client_main_app_db.post(
        "/auth/revoke",
        json={"refresh_token": rt3},
        headers=hdr,
    )
    assert r3.status_code == 429


def test_spent_jti_cleanup_removes_old_rows(db, monkeypatch):
    monkeypatch.setenv("AUTH_SPENT_JTI_RETENTION_DAYS", "30")
    old = datetime.now(timezone.utc) - timedelta(days=60)
    jti = "cleanup-test-jti-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    db.add(AuthSpentRefreshJti(jti=jti, spent_at=old))
    db.commit()
    n = run_spent_jti_cleanup(db)
    assert n >= 1
    assert db.query(AuthSpentRefreshJti).filter(AuthSpentRefreshJti.jti == jti).first() is None
