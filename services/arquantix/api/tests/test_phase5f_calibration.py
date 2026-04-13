"""Phase 5F — feedback, calibration suggestive, config poids, A/B déterministe."""
from __future__ import annotations

import pytest

from services.security.risk_calibration import compute_calibration_suggestions
from services.security.risk_config import get_risk_weight, runtime_weight_overrides
from services.security.risk_experiments import assign_variant, load_variant_weight_overrides
from services.security.risk_feedback import RiskFeedback, record_risk_feedback


def test_record_risk_feedback_no_raise():
    fb = RiskFeedback(
        action_key="wallet_transfer",
        user_id="u1",
        risk_score=42.0,
        risk_level="medium",
        decision="step_up",
        outcome="confirmed_fraud",
        feedback_type="fraud_confirmed",
        factor_codes=["device_new", "action_burst"],
        metadata={"ticket": "F-1"},
    )
    record_risk_feedback(fb)


def test_calibration_suggests_increase_on_fraud_pattern():
    fbs = []
    for i in range(6):
        fbs.append(
            RiskFeedback(
                action_key="wallet_transfer",
                user_id=f"u{i}",
                risk_score=60.0,
                risk_level="high",
                decision="step_up",
                outcome="fraud",
                feedback_type="fraud_confirmed",
                factor_codes=["device_new"],
            )
        )
    sug = compute_calibration_suggestions(fbs, min_samples_per_factor=5)
    assert any(s.factor_code == "device_new" and s.suggested_weight > s.current_weight for s in sug)


def test_calibration_suggests_decrease_on_false_positive_pattern():
    fbs = []
    for i in range(6):
        fbs.append(
            RiskFeedback(
                action_key="wallet_transfer",
                user_id=f"u{i}",
                risk_score=55.0,
                risk_level="high",
                decision="step_up",
                outcome="legitimate",
                feedback_type="false_positive",
                factor_codes=["device_new"],
            )
        )
    sug = compute_calibration_suggestions(fbs, min_samples_per_factor=5)
    assert any(s.factor_code == "device_new" and s.suggested_weight < s.current_weight for s in sug)


def test_assign_variant_deterministic():
    assert assign_variant("user-42", "exp_a") == assign_variant("user-42", "exp_a")


def test_experiment_variant_weights_json(monkeypatch):
    monkeypatch.setenv(
        "RISK_EXPERIMENT_VARIANT_A_WEIGHTS_JSON",
        '{"device_new": 22.0}',
    )
    ov = load_variant_weight_overrides("exp_test", "variant_a")
    assert ov.get("device_new") == 22.0
    assert load_variant_weight_overrides("exp_test", "control") == {}


def test_config_override_env(monkeypatch):
    monkeypatch.setenv("RISK_WEIGHT_DEVICE_NEW", "18")
    assert get_risk_weight("device_new") == 18.0


def test_runtime_weight_overrides_context():
    before = get_risk_weight("device_new")
    with runtime_weight_overrides({"device_new": 19.0}):
        assert get_risk_weight("device_new") == 19.0
    assert get_risk_weight("device_new") == before
