"""Tests moteur Zero Trust (politique, contexte, journalisation)."""
from __future__ import annotations

import pytest
from sqlalchemy import inspect

from database import engine
from services.security.zero_trust.decision_logging import persist_security_decision, should_persist_decision
from services.security.zero_trust.request_security_context import RequestSecurityContext
from services.security.zero_trust.security_policy_engine import evaluate_security_policy


def _ctx(**kw) -> RequestSecurityContext:
    defaults = {
        "user_id": 1,
        "session_id": None,
        "device_id": "dev-1",
        "device_hash": "ab" * 32,
        "device_trust_level": "TRUSTED",
        "device_reputation_blocked": False,
        "global_risk_score": 10,
        "fraud_score": None,
        "ip_address": "127.0.0.1",
        "geo_country": None,
        "step_up_required": False,
        "account_locked": False,
        "roles": ["admin"],
        "auth_strength": "otp",
        "attestation_status": "verified",
    }
    defaults.update(kw)
    return RequestSecurityContext(**defaults)  # type: ignore[arg-type]


def test_context_healthy_allow_api_access():
    r = evaluate_security_policy(_ctx(global_risk_score=5), "session.api_access", "*")
    assert r["allow"] is True
    assert r.get("require_step_up") is False


def test_elevated_risk_step_up_sensitive():
    r = evaluate_security_policy(_ctx(global_risk_score=75, auth_strength="otp"), "kyc.read", "person:x")
    assert r["require_step_up"] is True
    assert r["allow"] is False


def test_critical_risk_deny_sensitive():
    r = evaluate_security_policy(_ctx(global_risk_score=92, auth_strength="otp"), "kyc.read", "person:x")
    assert r["allow"] is False
    assert r["policy_id"] == "zt_sensitive_risk_deny"


def test_auth_strength_insufficient_revoke_all():
    r = evaluate_security_policy(_ctx(global_risk_score=10, auth_strength="password"), "auth.revoke_all", "user:1")
    assert r["allow"] is False
    assert "auth_strength" in (r.get("deny_reason") or "").lower()


def test_kyc_read_denied_support_readonly_role():
    r = evaluate_security_policy(
        _ctx(global_risk_score=5, auth_strength="otp", roles=["readonly"]),
        "kyc.write",
        "person:x",
    )
    assert r["allow"] is False
    assert r["policy_id"] == "zt_rbac_role_deny"


@pytest.fixture
def require_auth_security_decisions_table():
    insp = inspect(engine)
    if "auth_security_decisions" not in insp.get_table_names(schema="public"):
        pytest.skip("Table auth_security_decisions absente : exécuter alembic upgrade head (révision 116).")


def test_decision_logged_when_deny(db, require_auth_security_decisions_table):
    ctx = _ctx(global_risk_score=92, auth_strength="otp")
    result = evaluate_security_policy(ctx, "kyc.read", "person:test")
    assert should_persist_decision(result, "kyc.read") is True
    row = persist_security_decision(db, context=ctx, result=result, action="kyc.read", resource="person:test")
    db.flush()
    assert row is not None
    assert row.allow is False
    assert row.policy_id == "zt_sensitive_risk_deny"


def test_decryption_policy_kyc(monkeypatch):
    from services.security.zero_trust import data_access_control

    ctx = _ctx(global_risk_score=92, auth_strength="otp")
    ok, res = data_access_control.decryption_allowed(ctx, purpose="kyc_pii_read", resource="person:1")
    assert ok is False
    assert res.get("allow") is False
