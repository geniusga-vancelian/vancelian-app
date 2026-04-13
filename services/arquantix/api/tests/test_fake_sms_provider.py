"""FAKE_SMS_PROVIDER: dev/test simulated SMS without Twilio."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from database import AuditEvent, Person
from services.security.providers.fake_sms_provider import FakeSmsProvider
from services.security.providers.sms_provider import get_sms_provider
from services.security.two_factor_config_guard import TwoFactorConfigGuardError, run_two_factor_config_guard


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
    token = create_access_token({"sub": "fake-sms-test", "person_id": str(person_id)})
    return {"Authorization": f"Bearer {token}"}


def test_get_sms_provider_uses_fake_in_non_prod_when_flag(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("FAKE_SMS_PROVIDER", "true")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    p = get_sms_provider()
    assert isinstance(p, FakeSmsProvider)
    assert p.is_noop is False


def test_get_sms_provider_forbids_fake_in_production_like(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FAKE_SMS_PROVIDER", "true")
    with pytest.raises(RuntimeError, match="FAKE_SMS_PROVIDER"):
        get_sms_provider()


def test_config_guard_rejects_fake_sms_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SKIP_TWO_FACTOR_CONFIG_GUARD", raising=False)
    monkeypatch.setenv("TWO_FACTOR_REQUIRE_AUTH", "true")
    monkeypatch.setenv("TWO_FACTOR_TOTP_MASTER_KEY", "k" * 32)
    monkeypatch.setenv("FAKE_SMS_PROVIDER", "true")
    monkeypatch.setattr(
        "services.security.two_factor_config_guard.get_sms_provider",
        lambda: MagicMock(is_noop=False),
    )
    monkeypatch.setattr(
        "services.security.two_factor_config_guard.get_email_provider",
        lambda: MagicMock(is_noop=False),
    )
    with pytest.raises(TwoFactorConfigGuardError) as exc:
        run_two_factor_config_guard()
    assert "FAKE_SMS_PROVIDER" in str(exc.value)


def test_fake_sms_start_records_sent_audit_and_verify(client: TestClient, db: Session, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("FAKE_SMS_PROVIDER", "true")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWO_FACTOR_DEV_FIXED_CODE", raising=False)
    p = _person(db)
    h = _headers_for_person(p.id)
    with patch(
        "services.security.two_factor_service.new_plaintext_sms_otp",
        return_value="123456",
    ):
        r = client.post(
            "/api/2fa/start",
            json={"channel": "sms", "purpose": "withdrawal", "target": "+33700999887"},
            headers=h,
        )
    assert r.status_code == 200, r.text
    cid = r.json()["challenge_id"]
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.event_type == "two_factor.challenge.sent",
            AuditEvent.person_id == p.id,
        )
        .all()
    )
    assert rows
    assert any((row.payload or {}).get("provider") == "fake_sms" for row in rows)
    vr = client.post(
        "/api/2fa/verify",
        json={"challenge_id": cid, "code": "123456"},
        headers=h,
    )
    assert vr.status_code == 200, vr.text


def test_fake_sms_does_not_use_httpx(client: TestClient, db: Session, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("FAKE_SMS_PROVIDER", "true")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    p = _person(db)
    h = _headers_for_person(p.id)
    with patch("services.security.providers.sms_provider.httpx.Client") as client_ctor:
        r = client.post(
            "/api/2fa/start",
            json={"channel": "sms", "purpose": "withdrawal", "target": "+33700888777"},
            headers=h,
        )
    assert r.status_code == 200, r.text
    client_ctor.assert_not_called()
