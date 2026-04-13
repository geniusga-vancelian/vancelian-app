"""Tests Session Intelligence + continuous auth (logique décisionnelle, sans stack parallèle)."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.security.continuous_auth_engine import (
    ContinuousAuthDecision,
    evaluate_request_security_context,
    next_step_hint,
)
from services.security.sensitive_action_map import policy_for_action, tier_for_action
from services.security.session_intelligence_service import (
    compute_session_trust,
    evaluate_session_risk,
    should_force_reauth,
    should_require_step_up,
)


def _utcnow():
    return datetime.now(timezone.utc)


def test_policy_view_sensitive_data_strict_recent_and_step_up():
    p = policy_for_action("view_sensitive_data")
    assert p.requires_step_up is True
    assert p.requires_recent_auth_seconds == 600
    assert p.allowed_if_device_trusted_only is True


def test_tier_for_action_defaults_low():
    assert tier_for_action("unknown_op") == "low"
    assert tier_for_action("withdrawal") == "high"


def test_evaluate_session_risk_reasons():
    intel = SimpleNamespace(reason_codes_json=["ip_changed", "fingerprint_changed"], device_trust_level="LOW")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    r = evaluate_session_risk(db, user_id=1, intel=intel, fraud_hybrid=0.5)
    assert r >= 50


def test_compute_session_trust():
    intel = SimpleNamespace(
        last_risk_score=75,
        step_up_required=False,
        device_trust_level="HIGH",
        session_trust_level="HIGH",
    )
    assert compute_session_trust(intel) == "LOW"
    intel2 = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        device_trust_level="HIGH",
        session_trust_level="HIGH",
    )
    assert compute_session_trust(intel2) == "HIGH"


def test_continuous_auth_disabled_allows(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "false")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(last_risk_score=99, step_up_required=True)
    d = evaluate_request_security_context(sess, req, intel, sensitive_action="withdrawal")
    assert d.allow is True
    assert "continuous_auth_disabled" in d.reason_codes


def test_should_force_reauth_country(monkeypatch):
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "true")
    intel = SimpleNamespace(reason_codes_json=["country_changed"], last_risk_score=20)
    assert should_force_reauth(intel, "high") is True
    assert should_force_reauth(intel, "low") is False


def test_should_step_up_flag(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "true")
    intel = SimpleNamespace(step_up_required=True, last_risk_score=0)
    assert should_require_step_up(intel, "low") is True


def test_policy_withdrawal_high_and_step_up():
    p = policy_for_action("withdrawal")
    assert p.required_auth_level.value == "HIGH"
    assert p.requires_step_up is True


def test_next_step_hint_reauth():
    d = ContinuousAuthDecision(
        allow=False,
        require_step_up=False,
        require_reauth=True,
        require_biometric=False,
        reason_codes=["reauth_required"],
    )
    assert next_step_hint(d) == "full_reauth"


def test_continuous_auth_policy_recent_auth_forces_step_up(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "true")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=0,
        step_up_required=False,
        last_step_up_at=None,
        auth_strength="password_otp",
        device_trust_level="HIGH",
    )
    d = evaluate_request_security_context(sess, req, intel, sensitive_action="withdrawal")
    assert d.allow is False
    assert d.require_step_up is True
    assert "recent_auth_required" in d.reason_codes


def test_device_not_trusted_forces_step_up(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=0,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        auth_strength="passkey",
        device_trust_level="LOW",
    )
    d = evaluate_request_security_context(sess, req, intel, sensitive_action="view_sensitive_data")
    assert d.require_step_up is True
    assert "device_not_trusted" in d.reason_codes


def test_view_sensitive_data_allow_when_recent_step_up_and_trusted_device(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        auth_strength="password_otp",
        device_trust_level="HIGH",
    )
    d = evaluate_request_security_context(sess, req, intel, sensitive_action="view_sensitive_data")
    assert d.allow is True
    assert d.require_step_up is False
    assert "recent_auth_required" not in d.reason_codes


def test_view_sensitive_data_reauth_when_engine_requires_full_reauth(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "true")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=20,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        auth_strength="password_otp",
        device_trust_level="HIGH",
        reason_codes_json=["country_changed"],
    )
    d = evaluate_request_security_context(sess, req, intel, sensitive_action="view_sensitive_data")
    assert d.allow is False
    assert d.require_reauth is True
    assert d.require_step_up is False


def test_view_sensitive_data_recent_auth_stale_forces_step_up(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    from datetime import timedelta

    stale = _utcnow() - timedelta(seconds=700)
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=stale,
        auth_strength="password_otp",
        device_trust_level="HIGH",
    )
    d = evaluate_request_security_context(sess, req, intel, sensitive_action="view_sensitive_data")
    assert d.allow is False
    assert d.require_step_up is True
    assert "recent_auth_required" in d.reason_codes
