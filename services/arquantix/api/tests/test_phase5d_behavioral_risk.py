"""Phase 5D — risque comportemental déterministe (géo, appareil, rafales, overrides)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.security.continuous_auth_engine import evaluate_request_security_context
from services.security.risk_engine import (
    BehavioralRiskContext,
    _behavioral_action_burst,
    _geo_stability_bonus_factor,
    evaluate_request_risk,
    extract_behavioral_context,
)
from services.security.sensitive_action_map import policy_for_action


def _utcnow():
    return datetime.now(timezone.utc)


def _req(headers: dict) -> MagicMock:
    r = MagicMock()
    r.headers = headers
    r.client = MagicMock()
    r.client.host = "203.0.113.1"
    return r


def test_geo_same_country_no_velocity_penalty(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("GEO_VELOCITY_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
        last_country="FR",
    )
    b = BehavioralRiskContext(geo_country="FR", previous_geo_country="FR", last_action_timestamp=_utcnow())
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=100.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    codes = [f.code for f in ev.factors]
    assert "geo_velocity_anomaly" in codes
    gf = next(f for f in ev.factors if f.code == "geo_velocity_anomaly")
    assert gf.weight == 0.0
    gsb = next(f for f in ev.factors if f.code == "geo_stability_bonus")
    assert gsb.weight == -5.0


def test_geo_fast_country_change_forces_reauth(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("GEO_VELOCITY_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    past = _utcnow() - timedelta(minutes=15)
    b = BehavioralRiskContext(
        geo_country="FR",
        previous_geo_country="AE",
        last_action_timestamp=past,
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=100.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    assert ev.recommended_outcome == "reauth"
    assert ev.override_reason == "behavioral_force_reauth"
    assert "geo_impossible_travel" in ev.behavioral_flags
    assert "geo_stability_bonus" not in [f.code for f in ev.factors]


def test_known_device_lowers_score(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    b = BehavioralRiskContext(
        device_fingerprint_id="abc123",
        known_device_ids=["abc123", "xyz"],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=500.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    dc = next(f for f in ev.factors if f.code == "device_known")
    assert dc.weight < 0


def test_new_device_higher_score(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    b = BehavioralRiskContext(
        device_fingerprint_id="newfp",
        known_device_ids=["other1", "other2"],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=500.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    dc = next(f for f in ev.factors if f.code == "device_new")
    assert dc.weight > 0


def test_device_no_baseline_light_penalty(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    b = BehavioralRiskContext(
        device_fingerprint_id="first_fp",
        known_device_ids=[],
    )
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=500.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    dc = next(f for f in ev.factors if f.code == "device_no_baseline")
    assert dc.weight == 5.0


def test_geo_stability_bonus_unit():
    b = BehavioralRiskContext(
        geo_country="FR",
        previous_geo_country="FR",
        last_action_timestamp=_utcnow(),
    )
    intel = SimpleNamespace(last_country="FR", reason_codes_json=[])
    r = _geo_stability_bonus_factor(b, 0.0, intel)
    assert r is not None
    assert r.code == "geo_stability_bonus"
    assert r.weight == -5.0


def test_geo_stability_suppressed_when_velocity_anomaly():
    b = BehavioralRiskContext(
        geo_country="FR",
        previous_geo_country="FR",
        last_action_timestamp=_utcnow(),
    )
    intel = SimpleNamespace(last_country="FR", reason_codes_json=[])
    assert _geo_stability_bonus_factor(b, 15.0, intel) is None


def test_geo_stability_no_bonus_without_recent_or_stable_intel():
    b = BehavioralRiskContext(
        geo_country="FR",
        previous_geo_country="FR",
        last_action_timestamp=_utcnow() - timedelta(hours=48),
    )
    intel = SimpleNamespace(last_country="DE", reason_codes_json=[])
    assert _geo_stability_bonus_factor(b, 0.0, intel) is None


def test_burst_homogeneous_and_mixed_and_fallback():
    h = _behavioral_action_burst(4, "pay", ["pay", "pay", "pay"], None)
    assert h.code == "action_burst_homogeneous"
    assert h.weight == 20.0

    m = _behavioral_action_burst(4, "pay", ["pay", "transfer", "view"], None)
    assert m.code == "action_burst_mixed"
    assert m.weight == 10.0

    fb = _behavioral_action_burst(4, None, None, None)
    assert fb.code == "action_burst"
    assert fb.weight == 10.0

    cap = _behavioral_action_burst(8, None, None, None)
    assert cap.code == "action_burst"
    assert cap.weight == 25.0


def test_burst_high_value_forces_step_up(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    b = BehavioralRiskContext(action_count_last_5min=8)
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=2000.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    assert ev.recommended_outcome == "step_up"
    assert ev.override_reason == "behavioral_force_step_up"


def test_new_account_higher_risk(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    b = BehavioralRiskContext(account_creation_age_days=0.5)
    ev = evaluate_request_risk(
        action_key="view_sensitive_data",
        policy=policy_for_action("view_sensitive_data"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=None,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    ag = next(f for f in ev.factors if f.code == "account_age_risk")
    assert ag.weight >= 20


def test_new_device_high_amount_reauth(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("SESSION_REAUTH_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    b = BehavioralRiskContext(
        device_fingerprint_id="newone",
        known_device_ids=["a", "b"],
    )
    ev = evaluate_request_risk(
        action_key="withdrawal",
        policy=policy_for_action("withdrawal"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=20000.0,
        same_owner=None,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    assert ev.recommended_outcome == "reauth"
    assert "new_device_high_amount" in ev.behavioral_flags


def test_backward_compat_no_behavior_when_disabled(monkeypatch):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "false")
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
        request=_req({"X-Action-Count-Last-5min": "99"}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        session=MagicMock(),
    )
    codes = [f.code for f in ev.factors]
    assert "geo_velocity_anomaly" not in codes
    assert "action_burst" not in codes


def test_extract_behavioral_graceful(monkeypatch):
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    u = SimpleNamespace(created_at=_utcnow() - timedelta(days=100))
    sess = SimpleNamespace(fingerprint_hash="fp1", auth_strength="password")
    intel = SimpleNamespace(last_country="FR", auth_strength="password_otp", last_activity_at=_utcnow())
    r = _req(
        {
            "x-geo-country": "fr",
            "x-known-device-ids": "fp1,fp2",
            "x-action-type": "wallet_transfer",
            "x-recent-action-types": "wallet_transfer,view_balance",
            "x-same-type-action-count-5min": "2",
        }
    )
    ctx = extract_behavioral_context(r, u, intel, sess)
    assert ctx.geo_country == "FR"
    assert "fp1" in (ctx.known_device_ids or [])
    assert ctx.action_type == "wallet_transfer"
    assert ctx.recent_action_types == ["wallet_transfer", "view_balance"]
    assert ctx.same_type_action_count_5min == 2


def test_integration_known_small_transfer(monkeypatch):
    monkeypatch.setenv("CONTINUOUS_AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_ENABLED", "true")
    monkeypatch.setenv("GEO_VELOCITY_ENABLED", "true")
    monkeypatch.setenv("ADAPTIVE_FRICTION_ENABLED", "true")
    monkeypatch.setenv("LOW_RISK_TRANSFER_AMOUNT", "100")
    monkeypatch.setenv("LOW_RISK_RECENT_AUTH_SECONDS", "900")
    sess = SimpleNamespace(id=uuid.uuid4(), user_id=1, device_id="d", fingerprint_hash="kdev")
    req = MagicMock()
    req.headers = {
        "x-geo-country": "FR",
        "x-previous-geo-country": "FR",
        "x-known-device-ids": "kdev",
        "x-device-fingerprint": "kdev",
        "x-action-count-last-5min": "1",
    }
    req.client = MagicMock()
    req.client.host = "198.51.100.1"
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        auth_strength="passkey",
        device_trust_level="HIGH",
        reason_codes_json=[],
        last_country="FR",
        last_activity_at=_utcnow(),
    )
    u = SimpleNamespace(created_at=_utcnow() - timedelta(days=400))
    d = evaluate_request_security_context(
        sess,
        req,
        intel,
        sensitive_action="wallet_transfer",
        transfer_amount_eur=50.0,
        same_owner=True,
        current_user=u,
    )
    assert d.allow is True
    assert d.risk_score is not None


@pytest.mark.parametrize(
    "env_behavior,expect_behavior_factor",
    [
        ("true", True),
        ("false", False),
    ],
)
def test_behavioral_toggle(monkeypatch, env_behavior, expect_behavior_factor):
    monkeypatch.setenv("RISK_ENGINE_ENABLED", "true")
    monkeypatch.setenv("BEHAVIORAL_RISK_ENABLED", env_behavior)
    monkeypatch.setenv("SESSION_STEP_UP_ENABLED", "false")
    intel = SimpleNamespace(
        last_risk_score=5,
        step_up_required=False,
        last_step_up_at=_utcnow(),
        device_trust_level="HIGH",
        reason_codes_json=[],
    )
    b = BehavioralRiskContext(account_creation_age_days=0.1)
    ev = evaluate_request_risk(
        action_key="wallet_transfer",
        policy=policy_for_action("wallet_transfer"),
        request=_req({}),
        current_user=None,
        intelligence=intel,
        device_trust_level="HIGH",
        last_step_up_at=intel.last_step_up_at,
        amount_eur=50.0,
        same_owner=True,
        strict_decision_context={"require_reauth": False, "adaptive_friction_applied": False},
        behavioral_context=b,
    )
    has_age = any(f.code == "account_age_risk" for f in ev.factors)
    assert has_age is expect_behavior_factor
