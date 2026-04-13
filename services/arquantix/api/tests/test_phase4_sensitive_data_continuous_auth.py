"""Phase 4 — auth continue sur lectures identité/KYC et admin sécurité (view_sensitive_data)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash
from database import AdminUser, AuthSession, Person
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.security.continuous_auth_engine import ContinuousAuthDecision
from tests.conftest import make_linked_client


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _admin_with_bound_session(db, monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.get_intelligence_for_session",
        lambda *_a, **_k: MagicMock(
            last_risk_score=10,
            device_trust_level="LOW",
            last_step_up_at=_utcnow(),
        ),
    )
    email = f"phase4-{uuid.uuid4()}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()
    sid = uuid.uuid4()
    sess = AuthSession(
        id=sid,
        user_id=u.id,
        device_id="dev-phase4",
        refresh_jti=f"jti-{uuid.uuid4().hex[:16]}",
        expires_at=_utcnow() + timedelta(days=7),
    )
    db.add(sess)
    db.flush()
    token = create_access_token(build_user_jwt_access_base_claims(u), session_id=str(sid))
    headers = {"Authorization": f"Bearer {token}", "X-Device-ID": "dev-phase4"}
    return u, headers


def test_get_person_identity_401_when_continuous_auth_requires_reauth(
    client: TestClient, db: Session, monkeypatch
):
    _, headers = _admin_with_bound_session(db, monkeypatch)

    def fake_eval(*_a, **_k):
        return ContinuousAuthDecision(
            allow=False,
            require_reauth=True,
            require_step_up=False,
            require_biometric=False,
            reason_codes=["test_reauth"],
        )

    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.evaluate_request_security_context",
        fake_eval,
    )
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.client_id == linked.id).first()
    r = client.get(f"/api/persons/{person.id}/identity", headers=headers)
    assert r.status_code == 401
    body = r.json()
    assert body["detail"]["code"] == "session.reauth_required"
    assert body["detail"]["action_key"] == "view_sensitive_data"


def test_get_person_identity_403_when_continuous_auth_requires_step_up(
    client: TestClient, db: Session, monkeypatch
):
    _, headers = _admin_with_bound_session(db, monkeypatch)

    def fake_eval(*_a, **_k):
        return ContinuousAuthDecision(
            allow=False,
            require_reauth=False,
            require_step_up=True,
            require_biometric=False,
            reason_codes=["test_step_up"],
        )

    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.evaluate_request_security_context",
        fake_eval,
    )
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.client_id == linked.id).first()
    r = client.get(f"/api/persons/{person.id}/identity", headers=headers)
    assert r.status_code == 403
    body = r.json()
    assert body["detail"]["code"] == "session.step_up_required"
    assert body["detail"]["action_key"] == "view_sensitive_data"


def test_get_user_risk_integration_success_with_continuous_auth_mocks(
    client: TestClient, db: Session, monkeypatch
):
    """Une requête admin protégée émet view_sensitive_data et répond 200 si la décision autorise."""
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")
    u, headers = _admin_with_bound_session(db, monkeypatch)

    def fake_eval(*_a, **_k):
        return ContinuousAuthDecision(
            allow=True,
            require_reauth=False,
            require_step_up=False,
            require_biometric=False,
            reason_codes=["ok"],
        )

    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.evaluate_request_security_context",
        fake_eval,
    )
    r = client.get(f"/admin/security/user-risk/{u.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["user_id"] == u.id
