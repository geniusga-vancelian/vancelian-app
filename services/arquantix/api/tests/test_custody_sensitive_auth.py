"""Auth continue + hooks SIEM sur routes custody sensibles (retrait / bénéficiaire IBAN)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from auth import create_access_token, get_password_hash
from database import AdminUser, AuthSession
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.security.continuous_auth_engine import ContinuousAuthDecision

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _admin_with_bound_session(db, monkeypatch):
    """Admin + AuthSession + JWT avec ``sid`` ; intel mockée (pas de table auth_session_intelligence)."""
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.get_intelligence_for_session",
        lambda *_a, **_k: None,
    )
    email = f"cust-sens-{uuid.uuid4()}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()
    sid = uuid.uuid4()
    sess = AuthSession(
        id=sid,
        user_id=u.id,
        device_id="dev-custody-sens",
        refresh_jti=f"jti-{uuid.uuid4().hex[:16]}",
        expires_at=_utcnow() + timedelta(days=7),
    )
    db.add(sess)
    db.flush()
    # Pas d’insert dans auth_session_intelligence (table optionnelle en local) : l’intelligence
    # peut être absente ; les tests 401/403 moquent evaluate_request_security_context.
    token = create_access_token(build_user_jwt_access_base_claims(u), session_id=str(sid))
    headers = {**ADMIN_HEADERS, "Authorization": f"Bearer {token}"}
    return u, headers


def _full_minimal_withdrawal_context(client: TestClient, db):
    """Provider + client PE + compte client + dépôt pour permettre un POST simulate-withdrawal."""
    from tests.test_custody import _create_provider, _create_test_client, _create_client_account, _create_settlement_account

    pe_client = _create_test_client(client, db)
    provider = _create_provider(client, f"Bank-{uuid.uuid4().hex[:6]}")
    _create_client_account(client, provider["id"], pe_client["id"], db)
    _create_settlement_account(client, provider["id"])
    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 5000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )
    return pe_client


def test_simulate_withdrawal_401_when_continuous_auth_requires_reauth(
    client: TestClient, db, monkeypatch
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
    pe_client = _full_minimal_withdrawal_context(client, db)
    res = client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={"client_id": pe_client["id"], "amount": 100, "currency": "EUR"},
        headers=headers,
    )
    assert res.status_code == 401
    body = res.json()
    assert body["detail"]["code"] == "session.reauth_required"
    assert body["detail"]["action_key"] == "withdrawal"


def test_simulate_withdrawal_403_when_continuous_auth_requires_step_up(
    client: TestClient, db, monkeypatch
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
    pe_client = _full_minimal_withdrawal_context(client, db)
    res = client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={"client_id": pe_client["id"], "amount": 100, "currency": "EUR"},
        headers=headers,
    )
    assert res.status_code == 403
    body = res.json()
    assert body["detail"]["code"] == "session.step_up_required"
    assert body["detail"]["action_key"] == "withdrawal"


def test_simulate_withdrawal_without_bearer_401(client: TestClient, db):
    """OAuth2PasswordBearer : absence de jeton avant toute logique métier."""
    from tests.test_custody import _full_setup

    _, pe_client, _, _ = _full_setup(client, db)
    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 5000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )
    # Sans Authorization (retrait exige JWT)
    res = client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={"client_id": pe_client["id"], "amount": 100, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 401


def test_simulate_withdrawal_success_calls_completed_hook(client: TestClient, db, monkeypatch):
    from tests.conftest import make_admin_headers
    from tests.test_custody import _full_setup

    spy = MagicMock()
    _, pe_client, _, _ = _full_setup(client, db)
    monkeypatch.setattr("services.custody.router.record_sensitive_action_completed", spy)
    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 5000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )
    headers = {**ADMIN_HEADERS, **make_admin_headers(db)}
    res = client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={"client_id": pe_client["id"], "amount": 200, "currency": "EUR"},
        headers=headers,
    )
    assert res.status_code == 200
    w_calls = [c for c in spy.call_args_list if c.kwargs.get("action_key") == "withdrawal"]
    assert len(w_calls) == 1


def test_simulate_withdrawal_insufficient_funds_calls_failed_hook(client: TestClient, db, monkeypatch):
    from tests.conftest import make_admin_headers
    from tests.test_custody import _full_setup

    _, pe_client, _, _ = _full_setup(client, db)
    fail_spy = MagicMock()
    monkeypatch.setattr("services.custody.router.record_sensitive_action_failed", fail_spy)
    headers = {**ADMIN_HEADERS, **make_admin_headers(db)}
    res = client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={"client_id": pe_client["id"], "amount": 999999, "currency": "EUR"},
        headers=headers,
    )
    assert res.status_code == 400
    w_fails = [c for c in fail_spy.call_args_list if c.kwargs.get("action_key") == "withdrawal"]
    assert len(w_fails) == 1
    assert "insufficient" in w_fails[0].kwargs.get("reason", "").lower()


def test_create_client_account_403_beneficiary_step_up(client: TestClient, db, monkeypatch):
    _, headers = _admin_with_bound_session(db, monkeypatch)

    def fake_eval(*_a, **_k):
        return ContinuousAuthDecision(
            allow=False,
            require_reauth=False,
            require_step_up=True,
            require_biometric=False,
            reason_codes=["step_up_beneficiary"],
        )

    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.evaluate_request_security_context",
        fake_eval,
    )
    from tests.test_custody import _create_provider, _create_test_client

    pe_client = _create_test_client(client, db)
    provider = _create_provider(client, f"B-{uuid.uuid4().hex[:6]}")
    res = client.post(
        "/api/admin/custody/accounts/client",
        json={
            "provider_id": provider["id"],
            "account_type": "client_deposit_account",
            "currency": "EUR",
            "account_holder_name": "X",
            "client_id": pe_client["id"],
            "iban": f"DE{uuid.uuid4().hex[:16].upper()}",
        },
        headers=headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["action_key"] == "beneficiary_add"
