"""PR F.2 — règles combinées, pondération, baseline."""
from __future__ import annotations

import pytest

from services.auth.device_risk_engine_pr_f import RiskEvaluationContext, compute_risk_score
from services.auth.device_risk_engine_pr_f2 import (
    baseline_deviation_bonus,
    build_legacy_risk_reasons,
    compute_weighted_risk_score,
    evaluate_combination_rules,
    step_up_zone_score,
)
from services.security.security_env import (
    is_device_risk_baseline_enabled,
    is_device_risk_combination_rules_enabled,
    is_device_risk_weighted_score_enabled,
)


def _ctx(**kwargs):
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


def test_flags_default_off():
    assert is_device_risk_combination_rules_enabled() is False
    assert is_device_risk_baseline_enabled() is False
    assert is_device_risk_weighted_score_enabled() is False


def test_weighted_zero_matches_additive_zero(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_USE_WEIGHTED_SCORE", "true")
    assert is_device_risk_weighted_score_enabled() is True
    ctx = _ctx()
    w, _ = compute_weighted_risk_score(ctx)
    a = compute_risk_score(ctx)
    assert w == a == 0


def test_combination_new_device_country_block(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_COMBINATION_RULES", "true")
    ctx = _ctx(
        last_country="FR",
        current_country="DE",
    )
    out = evaluate_combination_rules(ctx=ctx, profile=None)
    assert out.triggered is True
    assert out.decision == "block"
    assert "rule_new_device_and_country_change" in out.reasons


def test_combination_ip_attestation_block(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_COMBINATION_RULES", "true")
    ctx = _ctx(
        last_ip="1.1.1.1",
        current_ip="9.9.9.9",
        device_trust_level="LOW",
        attestation_absent=True,
        last_country="FR",
        current_country="FR",
    )
    prof = object()
    out = evaluate_combination_rules(ctx=ctx, profile=prof)
    assert out.triggered is True
    assert out.decision == "block"
    assert "rule_ip_change_and_attestation_low" in out.reasons


def test_combination_churn_velocity_block(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_COMBINATION_RULES", "true")
    ctx = _ctx(device_churn_distinct_24h=2, velocity_count=1)
    prof = object()
    out = evaluate_combination_rules(ctx=ctx, profile=prof)
    assert out.triggered is True
    assert out.decision == "block"


def test_step_up_zone_score():
    s = step_up_zone_score()
    assert 0 <= s <= 100


def test_legacy_reasons_contains_signals():
    ctx = _ctx(device_trust_level="LOW", attestation_absent=True)
    r = build_legacy_risk_reasons(ctx)
    assert "device_trust_low" in r
    assert "attestation_absent" in r


def test_baseline_deviation_cold_start(monkeypatch, db):
    from sqlalchemy import inspect

    monkeypatch.setenv("DEVICE_RISK_ENABLE_BASELINE", "true")
    bind = db.get_bind()
    if bind is None or not inspect(bind).has_table("auth_user_risk_baselines", schema="public"):
        pytest.skip("Table auth_user_risk_baselines absente (migration 136).")

    from database import AuthUserRiskBaseline

    monkeypatch.delenv("DEVICE_RISK_BASELINE_MIN_SAMPLES", raising=False)
    uid = 999001
    db.query(AuthUserRiskBaseline).filter(AuthUserRiskBaseline.user_id == uid).delete()
    db.commit()
    row = AuthUserRiskBaseline(user_id=uid, baseline_sample_count=0)
    db.add(row)
    db.commit()

    ctx = _ctx(current_country="XX", current_ip="192.0.2.1")
    bonus, reasons = baseline_deviation_bonus(db, user_id=uid, ctx=ctx)
    assert bonus == 0
    assert reasons == []
