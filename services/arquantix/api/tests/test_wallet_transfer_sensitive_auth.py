"""Auth continue (wallet_transfer) — transfert interne custody + smoke PE."""
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

from tests.test_internal_transfer import ADMIN_HEADERS, _full_setup


def _utcnow():
    return datetime.now(timezone.utc)


def _admin_with_bound_session(db, monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.get_intelligence_for_session",
        lambda *_a, **_k: None,
    )
    email = f"wt-sens-{uuid.uuid4()}@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()
    sid = uuid.uuid4()
    sess = AuthSession(
        id=sid,
        user_id=u.id,
        device_id="dev-wt-sens",
        refresh_jti=f"jti-{uuid.uuid4().hex[:16]}",
        expires_at=_utcnow() + timedelta(days=7),
    )
    db.add(sess)
    db.flush()
    token = create_access_token(build_user_jwt_access_base_claims(u), session_id=str(sid))
    headers = {**ADMIN_HEADERS, "Authorization": f"Bearer {token}"}
    return u, headers


def test_internal_transfer_401_reauth_when_eval_denies(client: TestClient, db, monkeypatch):
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
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=500.0)
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 10.0,
            "currency": "EUR",
            "external_reference": f"xfer-{uuid.uuid4().hex[:8]}",
        },
        headers=headers,
    )
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "session.reauth_required"
    assert res.json()["detail"]["action_key"] == "wallet_transfer"


def test_internal_transfer_403_step_up_when_eval_denies(client: TestClient, db, monkeypatch):
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
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=500.0)
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 10.0,
            "currency": "EUR",
            "external_reference": f"xfer-{uuid.uuid4().hex[:8]}",
        },
        headers=headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "session.step_up_required"


def test_internal_transfer_completed_hook_on_success(client: TestClient, db, monkeypatch):
    from tests.conftest import make_admin_headers

    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=800.0)
    spy = MagicMock()
    monkeypatch.setattr("services.custody.router.record_sensitive_action_completed", spy)
    h = {**ADMIN_HEADERS, **make_admin_headers(db)}
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 50.0,
            "currency": "EUR",
            "external_reference": f"xfer-{uuid.uuid4().hex[:8]}",
        },
        headers=h,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
    w = [c for c in spy.call_args_list if c.kwargs.get("action_key") == "wallet_transfer"]
    assert len(w) == 1


def test_internal_transfer_failed_hook_on_insufficient(client: TestClient, db, monkeypatch):
    from tests.conftest import make_admin_headers

    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10.0)
    fail_spy = MagicMock()
    monkeypatch.setattr("services.custody.router.record_sensitive_action_failed", fail_spy)
    h = {**ADMIN_HEADERS, **make_admin_headers(db)}
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 9999.0,
            "currency": "EUR",
            "external_reference": f"xfer-{uuid.uuid4().hex[:8]}",
        },
        headers=h,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "failed"
    w = [c for c in fail_spy.call_args_list if c.kwargs.get("action_key") == "wallet_transfer"]
    assert len(w) == 1


def test_portfolio_engine_trades_post_requires_wallet_transfer_context(client: TestClient, db, monkeypatch):
    """Smoke PE : 403 step_up avant validation du corps (Depends avant body)."""
    _, headers = _admin_with_bound_session(db, monkeypatch)

    def fake_eval(*_a, **_k):
        return ContinuousAuthDecision(
            allow=False,
            require_reauth=False,
            require_step_up=True,
            require_biometric=False,
            reason_codes=["pe_step_up"],
        )

    monkeypatch.setattr(
        "services.security.session_intelligence_dependencies.evaluate_request_security_context",
        fake_eval,
    )
    res = client.post(
        "/api/portfolio-engine/trades",
        json={},
        headers=headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["action_key"] == "wallet_transfer"


def test_executions_post_without_bearer_returns_401(client: TestClient):
    """Appel « interne » sans jeton : échec avant le corps (OAuth2)."""
    res = client.post(
        "/api/portfolio-engine/executions",
        json={},
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "internal-svc@test.dev",
            "X-Actor-Roles": "admin",
        },
    )
    assert res.status_code == 401


def test_executions_post_jwt_without_actor_rbac_returns_403(client: TestClient, db):
    """JWT admin valide mais sans en-têtes acteur PE → require_admin_or_ops refuse."""
    from tests.conftest import make_admin_headers

    res = client.post(
        "/api/portfolio-engine/executions",
        json={},
        headers=make_admin_headers(db),
    )
    assert res.status_code == 403
