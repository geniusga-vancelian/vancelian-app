"""Production-hardening tests for the transverse 2FA module."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from database import AuditEvent, Person, TwoFactorChallenge
from services.security.two_factor_config_guard import TwoFactorConfigGuardError, run_two_factor_config_guard
from services.security.two_factor_exceptions import TwoFactorException
from services.security.two_factor_purposes import validate_purpose
from services.security.two_factor_target_policy import assert_target_allowed_for_person
from tests.conftest import make_linked_client
from tests.test_two_factor_api import _headers_for_person


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


def test_purpose_not_allowed_when_strict():
    with pytest.raises(TwoFactorException) as exc:
        validate_purpose("totally_unknown_purpose", relaxed=False)
    assert exc.value.code == "purpose_not_allowed"


def test_config_guard_fails_in_production_without_providers(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SKIP_TWO_FACTOR_CONFIG_GUARD", raising=False)
    monkeypatch.setenv("TWO_FACTOR_REQUIRE_AUTH", "true")
    monkeypatch.setenv("TWO_FACTOR_TOTP_MASTER_KEY", "k" * 32)
    noop_sms = MagicMock()
    noop_sms.is_noop = True
    noop_em = MagicMock()
    noop_em.is_noop = True
    monkeypatch.setattr(
        "services.security.two_factor_config_guard.get_sms_provider",
        lambda: noop_sms,
    )
    monkeypatch.setattr(
        "services.security.two_factor_config_guard.get_email_provider",
        lambda: noop_em,
    )
    with pytest.raises(TwoFactorConfigGuardError):
        run_two_factor_config_guard()


def test_config_guard_skips_when_not_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SKIP_TWO_FACTOR_CONFIG_GUARD", raising=False)
    run_two_factor_config_guard()


def test_cannot_verify_another_users_challenge(client: TestClient, db: Session):
    p1 = _person(db)
    p2 = _person(db)
    h1 = _headers_for_person(p1.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "email", "purpose": "login", "target": "x@y.z"},
        headers=h1,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["challenge_id"]
    h2 = _headers_for_person(p2.id)
    bad = client.post(
        "/api/2fa/verify",
        json={"challenge_id": cid, "code": "000000"},
        headers=h2,
    )
    assert bad.status_code == 404
    detail = bad.json().get("detail") or {}
    assert detail.get("code") == "challenge_not_found"


def test_sms_provider_failure_returns_503(client: TestClient, db: Session, monkeypatch):
    from services.security.two_factor_service import TwoFactorService

    sms = MagicMock()
    sms.is_noop = False
    sms.audit_provider_key = "twilio"
    sms.send_otp.side_effect = RuntimeError("twilio down")
    email = MagicMock()
    email.is_noop = True
    svc = TwoFactorService(sms, email)
    monkeypatch.setattr("services.security.router.get_two_factor_service", lambda: svc)

    p = _person(db)
    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/start",
        json={"channel": "sms", "purpose": "withdrawal", "target": "+33612345678"},
        headers=h,
    )
    assert r.status_code == 503
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "provider_unavailable"
    n = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.person_id == p.id).count()
    assert n == 0


def test_verify_email_target_mismatch_strict(db: Session):
    c = make_linked_client(db, email="owner@example.com")
    person = db.query(Person).filter(Person.id == c.person_id).first()
    assert person is not None
    with pytest.raises(TwoFactorException) as exc:
        assert_target_allowed_for_person(
            db,
            person,
            channel="email",
            target="other@example.com",
            purpose="verify_email",
            relaxed=False,
        )
    assert exc.value.code == "target_mismatch"


def test_verify_global_rate_limit(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setattr(
        "services.security.two_factor_rate_limits.VERIFY_FAIL_MAX_PER_PERSON",
        2,
    )
    monkeypatch.setattr(
        "services.security.router.is_two_factor_relaxed",
        lambda **kwargs: False,
    )
    p = _person(db)
    for _ in range(2):
        db.add(
            AuditEvent(
                id=uuid.uuid4(),
                person_id=p.id,
                event_type="two_factor.challenge.verify_failed",
                actor_type="user",
                actor_id=None,
                correlation_id=uuid.uuid4(),
                payload={},
                schema_version=1,
                created_at=datetime.now(timezone.utc),
            )
        )
    db.flush()

    h = _headers_for_person(p.id)
    r = client.post(
        "/api/2fa/verify",
        json={"challenge_id": str(uuid.uuid4()), "code": "123456"},
        headers=h,
    )
    assert r.status_code == 429
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "verify_rate_limited"
