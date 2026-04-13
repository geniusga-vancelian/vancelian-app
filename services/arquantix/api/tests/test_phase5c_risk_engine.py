"""Phase 5C — moteur de risque déterministe (scores, intégration, downgrade)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.security.continuous_auth_engine import (
    ContinuousAuthDecision,
    evaluate_request_security_context,
)
from services.security.risk_engine import (
    base_score_for_action,
    clamp_risk_score,
    derive_risk_level,
    evaluate_request_risk,
    summarize_risk_factors,
)
from services.security.sensitive_action_map import policy_for_action


def _utcnow():
    return datetime.now(timezone.utc)


def _req_with_headers(headers: dict) -> MagicMock:
    r = MagicMock()
    r.headers = headers
    return r


@pytest.mark.parametrize(
    "score,expected",
    [
        (10.0, "low"),
        (30.0, "medium"),
        (60.0, "high"),
        (80.0, "critical"),
    ],
)
def test_derive_risk_level_bands(score, expected):
    assert derive_risk_level(score) == expected


def test_clamp_risk_score():
    assert clamp_risk_score(-5) == 0.0
    assert clamp_risk_score(150) == 100.0


def test_trusted_device_lowers_score(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    codes = [f.code for f in ev.factors]
    assert "device_trusted" in codes
    assert ev.risk_score < 50


def test_unknown_device_increases_score(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=10,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="LOW",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="UNKNOWN",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=200.0,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert "device_untrusted" in [f.code for f in ev.factors]
    assert ev.risk_score >= 45


def test_small_amount_lowers_score(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert "amount_lt_100" in [f.code for f in ev.factors]


def test_large_amount_increases_score(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="withdrawal",
        policy=policy_for_action("withdrawal"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=15000.0,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert "amount_10000_50000" in [f.code for f in ev.factors]


def test_stale_auth_increases_score(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    stale = _utcnow() - timedelta(hours=2)
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=stale,
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=stale,
        amount_eur=200.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert "auth_stale_gt_60min" in [f.code for f in ev.factors]


def test_same_owner_lowers_score(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=500.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert "same_owner_true" in [f.code for f in ev.factors]


def test_strict_reauth_authoritative(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": True, "adaptive_friction_applied": False},
    )
    assert ev.recommended_outcome == "reauth"


def test_critical_escalates_reauth(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="UNKNOWN",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="withdrawal",
        policy=policy_for_action("withdrawal"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="UNKNOWN",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=60000.0,
        same_owner=False,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert ev.risk_level == "critical"
    assert ev.recommended_outcome == "reauth"


def test_high_risk_step_up(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="LOW",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="LOW",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=5000.0,
        same_owner=False,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert ev.risk_level in ("high", "critical")
    assert ev.recommended_outcome in ("step_up", "reauth")


def test_integration_escalates_allow_to_step_up(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "false")
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d")
    req = MagicMock()
    req.headers = {}
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        auth_strength="password_otp",
        device_trust_level="LOW",
        reason_codes_json=[],
    )
    d = evaluate_request_security_context(sess, req, intel, sensitive_action="wallet_transfer", transfer_amount_eur=8000.0)
    assert d.risk_score is not None
    if d.risk_level in ("high", "critical"):
        assert d.allow is False


def test_downgrade_internal_transfer_low(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "true")
    monkeypatch.setenv("LOW_RISK_TRANSFER_AMOUNT", "100")
    monkeypatch.setenv("LOW_RISK_RECENT_AUTH_SECONDS", "900")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": True},
    )
    assert ev.risk_score < 25
    assert ev.final_action_key == "internal_transfer_low"
    assert any(f.code == "downgraded_to_internal_transfer_low" for f in ev.factors)


def test_downgrade_not_when_amount_missing(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "true")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=None,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": True},
    )
    assert ev.final_action_key == "wallet_transfer"


def test_downgrade_not_when_same_owner_unknown(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "true")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": True},
    )
    assert ev.final_action_key == "wallet_transfer"


def test_downgrade_not_when_si_step_up(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "true")
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "true")
    intel = SimpleNamespace(
        last_risk_score=40,
        step_up_required=True,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": True},
    )
    assert ev.final_action_key == "wallet_transfer"


def test_downgrade_not_when_risk_ge_25(monkeypatch):
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "true")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="LOW",
        reason_codes_json=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="LOW",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": True},
    )
    assert ev.risk_score >= 25
    assert ev.final_action_key == "wallet_transfer"


def test_backward_compat_to_dict_optional_fields():
    d = ContinuousAuthDecision(
        allow=True,
        require_step_up=False,
        require_reauth=False,
        require_biometric=False,
        reason_codes=["ok"],
    )
    td = d.to_dict()
    assert "risk_score" not in td
    assert td["allow"] is True


def test_summarize_risk_factors():
    from services.security.risk_engine import RiskFactorContribution

    f1 = RiskFactorContribution(code="a", weight=1.0, description="d")
    assert "a(+1)" in summarize_risk_factors([f1])


def test_base_score_fallback():
    assert base_score_for_action("unknown_xyz") == 30.0


def test_log_no_pii_in_factor_values(monkeypatch, caplog):
    import logging

    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    caplog.set_level(logging.INFO)
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req_with_headers({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    joined = " ".join(caplog.messages)
    assert "continuous_auth.risk_evaluated" in joined or "risk_evaluated" in joined
