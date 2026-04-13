"""Dev/test fixed OTP (TWO_FACTOR_DEV_FIXED_CODE) — env guards and API flow."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from database import Person
from services.security.two_factor_env import (
    two_factor_dev_code_for_api_exposure,
    two_factor_dev_fixed_code,
)


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
    token = create_access_token({"sub": "2fa-dev-fixed", "person_id": str(person_id)})
    return {"Authorization": f"Bearer {token}"}


def test_two_factor_dev_fixed_code_none_in_production_like(monkeypatch):
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    for env in ("production", "prod", "staging"):
        monkeypatch.setenv("APP_ENV", env)
        monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
        assert two_factor_dev_fixed_code() is None
        assert two_factor_dev_code_for_api_exposure() is None


def test_two_factor_dev_fixed_code_respects_arquantix_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ARQUANTIX_ENV", "staging")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "222222")
    assert two_factor_dev_fixed_code() is None


def test_two_factor_dev_fixed_code_invalid_format_ignored(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "12")
    assert two_factor_dev_fixed_code() is None


def test_expose_requires_truthy_flag_and_fixed(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "444444")
    monkeypatch.delenv("TWO_FACTOR_DEV_EXPOSE_CODE", raising=False)
    assert two_factor_dev_code_for_api_exposure() is None
    monkeypatch.setenv("TWO_FACTOR_DEV_EXPOSE_CODE", "true")
    assert two_factor_dev_code_for_api_exposure() == "444444"


def test_start_email_verify_uses_fixed_code(client: TestClient, db: Session, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "606060")
    p = _person(db)
    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "email", "purpose": "verify_email", "target": "dev@fixed.code"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["challenge_id"]
    vr = client.post(
        "/api/2fa/verify",
        json={"challenge_id": cid, "code": "606060"},
        headers=h,
    )
    assert vr.status_code == 200, vr.text


def test_verify_wrong_code_with_fixed_otp_still_fails(client: TestClient, db: Session, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "707070")
    p = _person(db)
    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "email", "purpose": "login", "target": "x@y.z"},
        headers=h,
    )
    assert r.status_code == 200
    cid = r.json()["challenge_id"]
    bad = client.post(
        "/api/2fa/verify",
        json={"challenge_id": cid, "code": "000000"},
        headers=h,
    )
    assert bad.status_code == 422


def test_start_includes_dev_code_when_expose_enabled(client: TestClient, db: Session, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "818181")
    monkeypatch.setenv("TWO_FACTOR_DEV_EXPOSE_CODE", "true")
    p = _person(db)
    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "sms", "purpose": "withdrawal", "target": "+33699887766"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("dev_code") == "818181"


def test_totp_start_omits_dev_code_even_when_expose(client: TestClient, db: Session, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "919191")
    monkeypatch.setenv("TWO_FACTOR_DEV_EXPOSE_CODE", "true")
    p = _person(db)
    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "totp", "purpose": "totp_setup"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert "dev_code" not in r.json()
