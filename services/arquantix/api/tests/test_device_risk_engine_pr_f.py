"""PR F — moteur risque antifraude (score, seuils, signaux clés)."""
from __future__ import annotations

from services.auth.device_risk_engine_pr_f import (
    RiskEvaluationContext,
    compute_risk_score,
    decide_risk_action,
)
from services.auth.device_signature_failure_rl import reset_device_signature_failure_rl_for_tests
from services.auth.device_sensitive_action_velocity import reset_sensitive_action_velocity_for_tests
from services.security.security_env import is_device_risk_engine_pr_f_enabled


def _base(**kwargs):
    d = dict(
        device_trust_level="HIGH",
        attestation_absent=False,
        attestation_stale=False,
        last_ip="10.0.0.1",
        current_ip="10.0.0.1",
        last_country="FR",
        current_country="FR",
        velocity_count=0,
        signature_failure_count=0,
        device_churn_distinct_24h=0,
        session_is_new=False,
        login_failures_recent=0,
        refresh_failures_recent=0,
    )
    d.update(kwargs)
    return RiskEvaluationContext(**d)


def test_pr_f_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DEVICE_RISK_ENGINE_PR_F_ENABLED", raising=False)
    assert is_device_risk_engine_pr_f_enabled() is False


def test_compute_baseline_zero():
    assert compute_risk_score(_base()) == 0


def test_compute_trust_low():
    assert compute_risk_score(_base(device_trust_level="LOW")) == 40


def test_compute_trust_medium():
    assert compute_risk_score(_base(device_trust_level="MEDIUM")) == 15


def test_attestation_absent():
    assert compute_risk_score(_base(attestation_absent=True)) == 40


def test_attestation_stale():
    assert compute_risk_score(_base(attestation_stale=True)) == 20


def test_ip_change():
    assert (
        compute_risk_score(
            _base(last_ip="1.1.1.1", current_ip="2.2.2.2"),
        )
        == 15
    )


def test_country_change():
    assert (
        compute_risk_score(
            _base(last_country="FR", current_country="DE"),
        )
        == 25
    )


def test_velocity_high():
    assert compute_risk_score(_base(velocity_count=5)) == 20


def test_signature_failures():
    assert compute_risk_score(_base(signature_failure_count=2)) == 30


def test_device_churn():
    assert compute_risk_score(_base(device_churn_distinct_24h=3)) == 25
    assert compute_risk_score(_base(device_churn_distinct_24h=2)) == 12


def test_new_session():
    assert compute_risk_score(_base(session_is_new=True)) == 10


def test_auth_failures_cap():
    assert compute_risk_score(_base(login_failures_recent=5, refresh_failures_recent=5)) == 20


def test_score_capped_at_100():
    s = compute_risk_score(
        _base(
            device_trust_level="LOW",
            attestation_absent=True,
            last_ip="1.1.1.1",
            current_ip="2.2.2.2",
            last_country="FR",
            current_country="US",
            velocity_count=10,
            signature_failure_count=5,
            device_churn_distinct_24h=5,
            session_is_new=True,
            login_failures_recent=10,
            refresh_failures_recent=10,
        )
    )
    assert s == 100


def test_decide_thresholds_default(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ALLOW_THRESHOLD", "40")
    monkeypatch.setenv("DEVICE_RISK_BLOCK_THRESHOLD", "70")
    assert decide_risk_action(0) == "allow"
    assert decide_risk_action(39) == "allow"
    assert decide_risk_action(40) == "step_up"
    assert decide_risk_action(69) == "step_up"
    assert decide_risk_action(70) == "block"


def test_reset_helpers_noop_for_pr_f():
    reset_device_signature_failure_rl_for_tests()
    reset_sensitive_action_velocity_for_tests()
