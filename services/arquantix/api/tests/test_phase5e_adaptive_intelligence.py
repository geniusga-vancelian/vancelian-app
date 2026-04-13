"""Phase 5E — intelligence adaptive déterministe (segmentation + seuils dynamiques)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.security.risk_engine import (
    UserSegmentationInput,
    build_dynamic_thresholds_dict,
    derive_user_segment,
    evaluate_request_risk,
    extract_segmentation_inputs,
    resolve_low_risk_transfer_amount_eur_for_segment,
    segment_risk_thresholds,
    segment_score_adjustment_weight,
)
from services.security.sensitive_action_map import policy_for_action


def _utcnow():
    return datetime.now(timezone.utc)


def _req(headers: dict) -> MagicMock:
    r = MagicMock()
    r.headers = headers
    return r


def test_derive_segment_new_user():
    inp = UserSegmentationInput(account_age_days=3.0, historical_anomaly_count=0)
    assert derive_user_segment(inp) == "new_user"


def test_derive_segment_risky_overrides_new():
    inp = UserSegmentationInput(account_age_days=3.0, historical_anomaly_count=2)
    assert derive_user_segment(inp) == "risky_user"


def test_derive_segment_trusted():
    inp = UserSegmentationInput(
        account_age_days=100.0,
        historical_anomaly_count=0,
        kyc_level="VERIFIED",
    )
    assert derive_user_segment(inp) == "trusted_user"


def test_derive_segment_high_value():
    inp = UserSegmentationInput(account_age_days=30.0, total_volume_eur=60_000.0)
    assert derive_user_segment(inp) == "high_value_user"


def test_derive_segment_normal_when_sparse():
    assert derive_user_segment(UserSegmentationInput()) == "normal_user"
    assert derive_user_segment(None) == "normal_user"


def test_segment_weights_table():
    assert segment_score_adjustment_weight("trusted_user") == -10.0
    assert segment_score_adjustment_weight("high_value_user") == -5.0
    assert segment_score_adjustment_weight("new_user") == 10.0
    assert segment_score_adjustment_weight("risky_user") == 20.0
    assert segment_score_adjustment_weight("normal_user") == 0.0


def test_dynamic_thresholds_resolver():
    assert resolve_low_risk_transfer_amount_eur_for_segment("new_user") == 100.0
    assert resolve_low_risk_transfer_amount_eur_for_segment("trusted_user") == 2000.0
    d = build_dynamic_thresholds_dict("risky_user")
    assert d["device_tolerance"] < 1.0
    assert d["recent_auth_seconds"] == 120


def test_segment_risk_thresholds_vs_default():
    h, c = segment_risk_thresholds("trusted_user", default_high=50.0, default_critical=75.0)
    assert (h, c) == (60.0, 80.0)
    h2, c2 = segment_risk_thresholds("new_user", default_high=50.0, default_critical=75.0)
    assert (h2, c2) == (40.0, 65.0)
    h3, c3 = segment_risk_thresholds("normal_user", default_high=52.0, default_critical=76.0)
    assert (h3, c3) == (52.0, 76.0)


def test_evaluate_5e_new_user_stricter(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("ADAPTIVE_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    u = SimpleNamespace(created_at=_utcnow() - timedelta(days=2))
    ev = evaluate_request_risk(
        action_key="view_portfolio",
        policy=policy_for_action("view_portfolio"),
        request=_req({}),
        current_user=u,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=None,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert ev.user_segment == "new_user"
    adj = next(f for f in ev.factors if f.code == "user_segment_adjustment")
    assert adj.weight == 10.0
    assert ev.dynamic_thresholds_used is not None
    assert ev.dynamic_thresholds_used["low_risk_transfer_amount_eur"] == 100.0


def test_evaluate_5e_trusted_smoother(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("ADAPTIVE_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    u = SimpleNamespace(created_at=_utcnow() - timedelta(days=120), kyc_tier="VERIFIED")
    ev = evaluate_request_risk(
        action_key="view_portfolio",
        policy=policy_for_action("view_portfolio"),
        request=_req({}),
        current_user=u,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=None,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": True},
    )
    assert ev.user_segment == "trusted_user"
    adj = next(f for f in ev.factors if f.code == "user_segment_adjustment")
    assert adj.weight == -10.0
    # medium + trusted + adaptive friction → allow (Phase 5E)
    assert ev.recommended_outcome == "allow"


def test_evaluate_5e_risky_aggressive(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("ADAPTIVE_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
        historical_anomaly_count=3,
    )
    u = SimpleNamespace(created_at=_utcnow() - timedelta(days=120))
    # Base élevée + ajustement risky → niveau high → step_up (escalade friction)
    ev = evaluate_request_risk(
        action_key="beneficiary_add",
        policy=policy_for_action("beneficiary_add"),
        request=_req({}),
        current_user=u,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=None,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": True},
    )
    assert ev.user_segment == "risky_user"
    adj = next(f for f in ev.factors if f.code == "user_segment_adjustment")
    assert adj.weight == 20.0
    assert ev.recommended_outcome == "step_up"


def test_5e_disabled_backward_compat(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("ADAPTIVE_INTELLIGENCE_ENABLED", "false")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    u = SimpleNamespace(created_at=_utcnow() - timedelta(days=2))
    ev = evaluate_request_risk(
        action_key="view_portfolio",
        policy=policy_for_action("view_portfolio"),
        request=_req({}),
        current_user=u,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=None,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
    )
    assert ev.user_segment == "normal_user"
    assert not any(f.code == "user_segment_adjustment" for f in ev.factors)
    assert ev.dynamic_thresholds_used is None


def test_extract_segmentation_headers():
    r = _req(
        {
            "x-user-lifetime-volume-eur": "60000",
            "x-user-historical-anomaly-count": "0",
            "x-user-kyc-level": "VERIFIED",
        }
    )
    u = SimpleNamespace(created_at=_utcnow() - timedelta(days=200))
    intel = SimpleNamespace()
    ctx = extract_segmentation_inputs(r, u, intel)
    assert ctx.total_volume_eur == 60000.0
    assert derive_user_segment(ctx) == "high_value_user"


def test_deterministic_same_inputs_same_segment():
    inp = UserSegmentationInput(account_age_days=10.0, total_volume_eur=1000.0)
    assert derive_user_segment(inp) == derive_user_segment(inp)
