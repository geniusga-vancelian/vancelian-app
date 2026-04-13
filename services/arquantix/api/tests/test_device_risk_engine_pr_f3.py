"""PR F.3 — baseline temporelle et anomalies."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.auth.device_risk_engine_pr_f import RiskEvaluationContext
from services.auth.device_risk_engine_pr_f3 import (
    baseline_temporal_anomaly_score,
    infer_risk_action_type,
    update_advanced_baseline_from_observation,
    _welford_append,
    _weekday_distance,
)
from services.security.security_env import is_device_risk_advanced_baseline_enabled


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
        current_hour_utc=14,
        weekday_utc=1,
        session_duration_sec=3600.0,
        action_type="wallet_transfer",
    )
    d.update(kwargs)
    return RiskEvaluationContext(**d)


def test_advanced_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("DEVICE_RISK_ENABLE_ADVANCED_BASELINE", raising=False)
    assert is_device_risk_advanced_baseline_enabled() is False


def test_weekday_distance_wrap():
    assert _weekday_distance(0.0, 6.0) == 1.0


def test_welford_monotonic_n():
    s = _welford_append(None, 10.0)
    s2 = _welford_append(s, 12.0)
    assert s2["n"] == 2


def test_infer_action_type_paths():
    from types import SimpleNamespace

    r1 = SimpleNamespace(url=SimpleNamespace(path="/api/internal-transfer"))
    r2 = SimpleNamespace(url=SimpleNamespace(path="/x/y"))
    assert infer_risk_action_type(r1) == "wallet_transfer"
    assert infer_risk_action_type(r2) == "sensitive_other"


def test_night_owl_no_time_anomaly(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_ADVANCED_BASELINE", "true")
    monkeypatch.setenv("DEVICE_RISK_ADVANCED_BASELINE_MIN_SAMPLES", "1")

    row = MagicMock()
    row.baseline_sample_count = 20
    row.avg_hour_of_day = 3.0
    row.std_hour_of_day = 4.0
    row.avg_weekday = 1.0
    row.std_weekday = 2.0
    row.avg_session_duration_sec = 100.0
    row.std_session_duration_sec = 50.0
    row.actions_per_hour_ema = 1.0
    row.last_10_actions_types = ["wallet_transfer", "wallet_transfer"]

    def _fake_get(_db, uid):
        return row

    import services.auth.device_risk_engine_pr_f3 as m

    monkeypatch.setattr(m, "_get_or_create_baseline", _fake_get)

    ctx = _ctx(current_hour_utc=3, weekday_utc=1, session_duration_sec=120.0, velocity_count=1)
    pts, reasons = baseline_temporal_anomaly_score(None, user_id=1, ctx=ctx)
    assert "baseline_time_anomaly" not in reasons
    assert pts < 20


def test_off_hours_spikes(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_ADVANCED_BASELINE", "true")
    monkeypatch.setenv("DEVICE_RISK_ADVANCED_BASELINE_MIN_SAMPLES", "1")

    row = MagicMock()
    row.baseline_sample_count = 20
    row.avg_hour_of_day = 14.0
    row.std_hour_of_day = 1.5
    row.avg_weekday = 2.0
    row.std_weekday = 1.0
    row.avg_session_duration_sec = 100.0
    row.std_session_duration_sec = 20.0
    row.actions_per_hour_ema = 0.5
    row.last_10_actions_types = ["beneficiary_add"] * 8

    def _fake_get(_db, uid):
        return row

    import services.auth.device_risk_engine_pr_f3 as m

    monkeypatch.setattr(m, "_get_or_create_baseline", _fake_get)

    ctx = _ctx(current_hour_utc=3, weekday_utc=2, action_type="wallet_transfer", velocity_count=10)
    pts, reasons = baseline_temporal_anomaly_score(None, user_id=1, ctx=ctx)
    assert "baseline_time_anomaly" in reasons or pts > 0


def test_update_advanced_requires_flag(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_ADVANCED_BASELINE", "false")
    from unittest.mock import MagicMock

    req = MagicMock()
    update_advanced_baseline_from_observation(
        None,
        user_id=1,
        ctx=_ctx(),
        request=req,
        session=None,
    )
