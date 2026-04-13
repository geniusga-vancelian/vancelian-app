"""POST /auth/security/local-passcode-ack — ACK passcode local (sans secret)."""
from __future__ import annotations

import uuid

import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jose import jwt as jose_jwt

from auth import ALGORITHM, SECRET_KEY, create_access_token, get_password_hash
from database import AdminUser, Person, TwoFactorChallenge
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims

from services.customers_admin.registration_progress import compute_canonical_registration_progress
from services.customers_admin.schemas import RegistrationMacroStage


@pytest.fixture(autouse=True)
def _disable_auth_side_effects_for_ack(monkeypatch):
    """Évite step-up session / fraude qui bloquent le 2e POST ACK avec le même user."""
    monkeypatch.setenv("LOGIN_FRAUD_ML_EVALUATION_ENABLED", "false")
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "false")
    monkeypatch.setenv("LOGIN_AUTH_STRATEGY_ENABLED", "false")
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "false")


def _mobile_user(db: Session) -> tuple[AdminUser, Person, str]:
    email = f"m-{uuid.uuid4().hex[:8]}@mobile.local"
    p = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={"collected": {}},
        kyc_status="not_started",
    )
    db.add(p)
    db.flush()
    u = AdminUser(
        email=email,
        hashed_password=get_password_hash("x"),
        person_id=p.id,
    )
    db.add(u)
    db.flush()
    token = create_access_token(build_user_jwt_access_base_claims(u))
    return u, p, token


def test_local_passcode_ack_success(client: TestClient, db: Session):
    _, p, token = _mobile_user(db)
    r = client.post(
        "/auth/security/local-passcode-ack",
        headers={"Authorization": f"Bearer {token}", "X-Device-ID": "dev-ack-1"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "local_passcode_registered_at" in data
    assert data.get("already_acknowledged") is False
    assert data.get("access_token")
    assert data.get("refresh_token")
    full = jose_jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert full.get("sec_inc") is not True
    assert full.get("acct_st") == "ACTIVE"
    db.expire_all()
    p2 = db.query(Person).filter(Person.id == p.id).first()
    assert p2 is not None
    sec = (p2.profile_json or {}).get("security") or {}
    assert sec.get("local_passcode_registered_at")
    assert sec.get("local_passcode_ack_device_id") == "dev-ack-1"


def test_local_passcode_ack_idempotent(client: TestClient, db: Session):
    _, p, token = _mobile_user(db)
    r1 = client.post(
        "/auth/security/local-passcode-ack",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    ts = r1.json()["local_passcode_registered_at"]
    at1 = r1.json()["access_token"]
    assert at1
    r2 = client.post(
        "/auth/security/local-passcode-ack",
        headers={"Authorization": f"Bearer {at1}"},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["already_acknowledged"] is True
    assert body2["local_passcode_registered_at"] == ts
    assert body2.get("access_token")
    db.expire_all()
    p2 = db.query(Person).filter(Person.id == p.id).first()
    sec = (p2.profile_json or {}).get("security") or {}
    assert sec.get("local_passcode_registered_at") == ts


def test_local_passcode_ack_requires_auth(client: TestClient, db: Session):
    _mobile_user(db)
    r = client.post("/auth/security/local-passcode-ack")
    assert r.status_code == 401


def test_local_passcode_ack_rejects_user_without_person(client: TestClient, db: Session):
    email = f"nop-{uuid.uuid4().hex[:8]}@admin.local"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"), person_id=None)
    db.add(u)
    db.flush()
    token = create_access_token(build_user_jwt_access_base_claims(u))
    r = client.post(
        "/auth/security/local-passcode-ack",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_registration_progress_passcode_true_after_ack(client: TestClient, db: Session):
    _, p, token = _mobile_user(db)
    client.post(
        "/auth/security/local-passcode-ack",
        headers={"Authorization": f"Bearer {token}"},
    )
    db.expire_all()
    p2 = db.query(Person).filter(Person.id == p.id).first()
    r = compute_canonical_registration_progress(db, p2, None)
    assert r.foundation.passcode_created is True


def test_account_secured_label_includes_pin_when_ack_and_mobile_verified(
    client: TestClient, db: Session
):
    _, p, token = _mobile_user(db)
    p.profile_json = {"collected": {"phone_e164": "+33123456789"}}
    db.add(p)
    db.flush()
    db.add(
        TwoFactorChallenge(
            id=uuid.uuid4(),
            person_id=p.id,
            channel="sms",
            target="+33123456789",
            code_hash="x",
            expires_at=datetime.now(timezone.utc),
            attempts=0,
            status="verified",
            purpose="login",
        )
    )
    db.flush()
    client.post(
        "/auth/security/local-passcode-ack",
        headers={"Authorization": f"Bearer {token}"},
    )
    db.expire_all()
    p2 = db.query(Person).filter(Person.id == p.id).first()
    r = compute_canonical_registration_progress(db, p2, None)
    assert r.stage == RegistrationMacroStage.ACCOUNT_SECURED
    assert "PIN" in r.label
