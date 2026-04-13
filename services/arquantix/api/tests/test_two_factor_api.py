"""Tests for /api/2fa (OTP + TOTP)."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from database import Person, TwoFactorChallenge


@pytest.fixture(autouse=True)
def _two_factor_dev_auth(monkeypatch):
    monkeypatch.setenv("TWO_FACTOR_REQUIRE_AUTH", "false")


def _person(db: Session) -> Person:
    p = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={},
        kyc_status="not_started",
    )
    db.add(p)
    db.flush()
    return p


def _headers_for_person(person_id) -> dict:
    token = create_access_token({"sub": "2fa-test-user", "person_id": str(person_id)})
    return {"Authorization": f"Bearer {token}"}


def test_start_email_challenge_and_verify(client: TestClient, db: Session):
    p = _person(db)
    h = _headers_for_person(p.id)
    with patch(
        "services.security.two_factor_service.new_plaintext_sms_otp",
        return_value="424242",
    ):
        r = client.post(
            "/api/2fa/start",
            json={"channel": "email", "purpose": "verify_email", "target": "user@example.com"},
            headers=h,
        )
    assert r.status_code == 200, r.text
    data = r.json()
    cid = data["challenge_id"]
    assert data["masked_target"] and "@" in data["masked_target"]

    row = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.id == uuid.UUID(cid)).first()
    assert row is not None
    assert row.status == "pending"

    vr = client.post(
        "/api/2fa/verify",
        json={"challenge_id": cid, "code": "424242"},
        headers=h,
    )
    assert vr.status_code == 200, vr.text
    assert vr.json()["success"] is True
    db.expire_all()
    row2 = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.id == uuid.UUID(cid)).first()
    assert row2.status == "verified"


def test_verify_wrong_code_increments_attempts(client: TestClient, db: Session):
    p = _person(db)
    h = _headers_for_person(p.id)
    with patch(
        "services.security.two_factor_service.new_plaintext_sms_otp",
        return_value="111111",
    ):
        r = client.post(
            "/api/2fa/start",
            json={"channel": "email", "purpose": "login", "target": "a@b.co"},
            headers=h,
        )
    cid = r.json()["challenge_id"]
    for _ in range(4):
        bad = client.post(
            "/api/2fa/verify",
            json={"challenge_id": cid, "code": "000000"},
            headers=h,
        )
        assert bad.status_code == 422
    row = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.id == uuid.UUID(cid)).first()
    assert row.attempts == 4


def test_rate_limit_second_start(client: TestClient, db: Session):
    p = _person(db)
    h = _headers_for_person(p.id)
    body = {"channel": "sms", "purpose": "withdrawal", "target": "+33612345678"}
    r1 = client.post("/api/2fa/start", json=body, headers=h)
    assert r1.status_code == 200
    r2 = client.post("/api/2fa/start", json=body, headers=h)
    assert r2.status_code == 429


def test_expired_challenge(client: TestClient, db: Session):
    p = _person(db)
    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "email", "purpose": "verify_email", "target": "x@y.z"},
        headers=h,
    )
    cid = uuid.UUID(r.json()["challenge_id"])
    row = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.id == cid).first()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    vr = client.post(
        "/api/2fa/verify",
        json={"challenge_id": str(cid), "code": "123456"},
        headers=h,
    )
    assert vr.status_code == 410


def test_totp_enroll_and_verify_flow(client: TestClient, db: Session):
    import pyotp

    p = _person(db)
    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "totp", "purpose": "totp_setup"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    url = r.json().get("otpauth_url")
    assert url
    cid = r.json()["challenge_id"]

    secret = pyotp.parse_uri(url).secret
    code = pyotp.TOTP(secret).now()

    vr = client.post(
        "/api/2fa/verify",
        json={"challenge_id": cid, "code": code},
        headers=h,
    )
    assert vr.status_code == 200, vr.text

    db.refresh(p)
    sec = (p.profile_json or {}).get("security") or {}
    assert sec.get("totp_secret_cipher")
    assert "totp_pending_cipher" not in sec

    r2 = client.post(
        "/api/2fa/start",
        json={"channel": "totp", "purpose": "login"},
        headers=h,
    )
    assert r2.status_code == 200
    cid2 = r2.json()["challenge_id"]
    code2 = pyotp.TOTP(secret).now()
    vr2 = client.post(
        "/api/2fa/verify",
        json={"challenge_id": cid2, "code": code2},
        headers=h,
    )
    assert vr2.status_code == 200
