"""Phase 5B — friction adaptive déterministe (avant moteur de risque complet)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.security.continuous_auth_engine import evaluate_request_security_context


def _utcnow():
    return datetime.now(timezone.utc)


def _base_env(monkeypatch) -> None:
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "true")
    monkeypatch.setenv("LOW_RISK_TRANSFER_AMOUNT", "100")
    monkeypatch.setenv("LOW_RISK_RECENT_AUTH_SECONDS", "900")


def test_wallet_small_transfer_no_step_up(monkeypatch):
    _base_env(monkeypatch)
    stale_for_policy = _utcnow() - timedelta(seconds=700)
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=stale_for_policy,
        auth_strength="password_otp",
        device_trust_level="HIGH",
    )
    d = evaluate_request_security_context(
        sess,
        req,
        intel,
        sensitive_action="wallet_transfer",
        transfer_amount_eur=50.0,
    )
    assert d.allow is True
    assert d.require_step_up is False
    assert "adaptive_low_friction_transfer" in d.reason_codes


def test_wallet_large_transfer_still_step_up(monkeypatch):
    _base_env(monkeypatch)
    stale_for_policy = _utcnow() - timedelta(seconds=700)
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=stale_for_policy,
        auth_strength="password_otp",
        device_trust_level="HIGH",
    )
    d = evaluate_request_security_context(
        sess,
        req,
        intel,
        sensitive_action="wallet_transfer",
        transfer_amount_eur=500.0,
    )
    assert d.allow is False
    assert d.require_step_up is True
    assert "recent_auth_required" in d.reason_codes


def test_wallet_unknown_device_step_up(monkeypatch):
    _base_env(monkeypatch)
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        auth_strength="password_otp",
        device_trust_level="LOW",
    )
    d = evaluate_request_security_context(
        sess,
        req,
        intel,
        sensitive_action="wallet_transfer",
        transfer_amount_eur=10.0,
    )
    assert d.allow is False
    assert d.require_step_up is True
    assert "device_not_trusted" in d.reason_codes


def test_wallet_stale_session_step_up(monkeypatch):
    _base_env(monkeypatch)
    stale = _utcnow() - timedelta(seconds=2000)
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=stale,
        auth_strength="password_otp",
        device_trust_level="HIGH",
    )
    d = evaluate_request_security_context(
        sess,
        req,
        intel,
        sensitive_action="wallet_transfer",
        transfer_amount_eur=10.0,
    )
    assert d.allow is False
    assert d.require_step_up is True


def test_wallet_si_risk_step_up_not_downgraded(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "true")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    intel = SimpleNamespace(
        last_risk_score=40,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        auth_strength="password_otp",
        device_trust_level="HIGH",
    )
    d = evaluate_request_security_context(
        sess,
        req,
        intel,
        sensitive_action="wallet_transfer",
        transfer_amount_eur=10.0,
    )
    assert d.allow is False
    assert d.require_step_up is True
    assert "adaptive_low_friction_transfer" not in d.reason_codes


def test_view_sensitive_adaptive_when_stale_within_low_risk_window(monkeypatch):
    _base_env(monkeypatch)
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
    assert d.allow is True
    assert d.require_step_up is False
    assert "adaptive_low_friction_view_sensitive" in d.reason_codes
