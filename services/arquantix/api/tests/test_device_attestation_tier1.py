"""Attestation matérielle Tier 1 — service, login/refresh, anti-rejeu nonce."""
from __future__ import annotations

import base64
import json
import uuid

import pytest
from sqlalchemy import inspect as sa_inspect

from jose import jwt as jose_jwt

from auth import ALGORITHM, SECRET_KEY, get_password_hash
from database import AdminUser, get_db
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests
from services.auth.device_attestation_service import mint_attestation_nonce, verify_device_attestation


def _require_migration_112():
    from database import engine

    cols = {c["name"] for c in sa_inspect(engine).get_columns("auth_sessions", schema="public")}
    if "device_trust_level" not in cols:
        pytest.skip("Appliquer la migration 112 (auth device attestation)")


@pytest.fixture(autouse=True)
def _rl_reset():
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture
def client_main_app_db(db):
    from main import app

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def test_verify_play_integrity_lenient_valid(db, monkeypatch):
    _require_migration_112()
    monkeypatch.setenv("DEVICE_ATTESTATION_STRICT", "false")
    nonce, _ = mint_attestation_nonce(db=db, platform="android", device_id="d1")
    payload = {
        "format": "play_integrity",
        "integrity_token": "test-token-" + uuid.uuid4().hex,
        "nonce": nonce,
        "verdict": {"basicIntegrity": True, "deviceIntegrity": "MEETS_BASIC_INTEGRITY"},
    }
    r = verify_device_attestation("android", payload, "d1", db=db)
    assert r.is_valid
    assert r.attestation_type == "play_integrity"


def test_verify_unknown_format_rejected():
    r = verify_device_attestation("ios", {"format": "fake_vendor"}, "dev")
    assert not r.is_valid
    assert any("unknown" in f.lower() for f in r.risk_flags)


def test_login_with_valid_attestation_header(client_main_app_db, db, monkeypatch):
    _require_migration_112()
    monkeypatch.setenv("DEVICE_ATTESTATION_ENABLED", "true")
    monkeypatch.setenv("DEVICE_ATTESTATION_STRICT", "false")
    monkeypatch.setenv("DEVICE_ATTESTATION_FAIL_BLOCKS_LOGIN", "false")

    email = "attest_ok@example.com"
    db.add(AdminUser(email=email, hashed_password=get_password_hash("pw")))
    db.commit()

    ch = client_main_app_db.post(
        "/auth/attestation/challenge",
        json={"platform": "android"},
        headers={"X-Device-ID": "mobile-dev-1"},
    )
    assert ch.status_code == 200
    nonce = ch.json()["nonce"]

    body = {
        "format": "play_integrity",
        "integrity_token": "tok-" + uuid.uuid4().hex,
        "nonce": nonce,
        "verdict": {"strongIntegrity": True},
    }
    header_val = base64.urlsafe_b64encode(json.dumps(body).encode()).decode().rstrip("=")

    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "pw"},
        headers={"X-Device-ID": "mobile-dev-1", "X-Device-Attestation": header_val},
    )
    assert login.status_code == 200
    access = login.json()["access_token"]
    claims = jose_jwt.decode(access, SECRET_KEY, algorithms=[ALGORITHM])
    assert claims.get("dtrust") == "TRUSTED"


def test_fake_attestation_blocks_when_configured(client_main_app_db, db, monkeypatch):
    _require_migration_112()
    monkeypatch.setenv("DEVICE_ATTESTATION_ENABLED", "true")
    monkeypatch.setenv("DEVICE_ATTESTATION_FAIL_BLOCKS_LOGIN", "true")

    email = "attest_block@example.com"
    db.add(AdminUser(email=email, hashed_password=get_password_hash("pw")))
    db.commit()

    body = {"format": "play_integrity", "nonce": "not-a-real-nonce", "integrity_token": "x"}
    header_val = json.dumps(body)

    r = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "pw"},
        headers={"X-Device-ID": "mobile-dev-2", "X-Device-Attestation": header_val},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "DEVICE_ATTESTATION_FAILED"


def test_replay_nonce_second_login_fails(client_main_app_db, db, monkeypatch):
    _require_migration_112()
    monkeypatch.setenv("DEVICE_ATTESTATION_ENABLED", "true")
    monkeypatch.setenv("DEVICE_ATTESTATION_STRICT", "false")
    monkeypatch.setenv("DEVICE_ATTESTATION_FAIL_BLOCKS_LOGIN", "true")

    email = "attest_replay@example.com"
    db.add(AdminUser(email=email, hashed_password=get_password_hash("pw")))
    db.commit()

    ch = client_main_app_db.post(
        "/auth/attestation/challenge",
        json={"platform": "android"},
        headers={"X-Device-ID": "mobile-dev-3"},
    )
    nonce = ch.json()["nonce"]
    body = {
        "format": "play_integrity",
        "integrity_token": "same-tok",
        "nonce": nonce,
        "verdict": {"basicIntegrity": True},
    }
    h = {"X-Device-ID": "mobile-dev-3", "X-Device-Attestation": json.dumps(body)}

    assert client_main_app_db.post("/auth/login", json={"email": email, "password": "pw"}, headers=h).status_code == 200
    r2 = client_main_app_db.post("/auth/login", json={"email": email, "password": "pw"}, headers=h)
    assert r2.status_code == 403
