"""PR F.7.2 — scoring temporel + persistance safe."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from services.auth.device_risk_engine_pr_f import RiskEvaluationContext
from services.auth.device_risk_temporal_engine import (
    apply_temporal_risk_overlay,
    compute_temporal_risk_score,
    persist_user_temporal_features,
)


def _req(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
        }
    )


def _ctx(*, hour: int = 14, wday: int = 2) -> RiskEvaluationContext:
    return RiskEvaluationContext(
        device_trust_level="HIGH",
        attestation_absent=False,
        attestation_stale=False,
        last_ip=None,
        current_ip=None,
        last_country=None,
        current_country=None,
        velocity_count=0,
        signature_failure_count=0,
        device_churn_distinct_24h=0,
        session_is_new=False,
        login_failures_recent=0,
        refresh_failures_recent=0,
        current_hour_utc=hour,
        weekday_utc=wday,
        action_type="sensitive_other",
    )


def _baseline_full() -> dict:
    h = {str(i): (1.0 / 24) for i in range(24)}
    w = {str(i): (1.0 / 7) for i in range(7)}
    return {
        "hour_distribution": h,
        "weekday_distribution": w,
        "action_transition_matrix": {"login->withdrawal": 0.5},
        "activity_rate_ema": 10.0,
    }


def test_temporal_score_zero_when_normal():
    current = {
        "total_samples_30d": 50,
        "activity_rate_7d": 10.0,
    }
    with patch(
        "services.auth.device_risk_temporal_engine.get_last_action_before_now",
        return_value=None,
    ):
        raw, reasons = compute_temporal_risk_score(
            current,
            _baseline_full(),
            ctx=_ctx(hour=14, wday=2),
            request=_req("/x"),
            db=MagicMock(),
            user_id=1,
        )
    assert raw == 0
    assert reasons == []


def test_temporal_score_zero_when_insufficient_samples(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_MIN_SAMPLES", "20")
    current = {"total_samples_30d": 5, "activity_rate_7d": 1.0}
    raw, reasons = compute_temporal_risk_score(
        current,
        _baseline_full(),
        ctx=_ctx(),
        request=_req("/x"),
        db=MagicMock(),
        user_id=1,
    )
    assert raw == 0
    assert reasons == []


def test_hour_anomaly(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_MIN_SAMPLES", "5")
    bl = _baseline_full()
    bl["hour_distribution"] = {str(i): (0.001 if i != 14 else 0.985) for i in range(24)}
    current = {"total_samples_30d": 20, "activity_rate_7d": 10.0}
    raw, reasons = compute_temporal_risk_score(
        current,
        bl,
        ctx=_ctx(hour=3),
        request=_req("/x"),
        db=MagicMock(),
        user_id=1,
    )
    assert raw > 0
    assert "temporal_hour_anomaly" in reasons


def test_weekday_anomaly(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_MIN_SAMPLES", "5")
    bl = _baseline_full()
    bl["weekday_distribution"] = {str(i): (0.001 if i != 2 else 0.994) for i in range(7)}
    current = {"total_samples_30d": 20, "activity_rate_7d": 10.0}
    raw, reasons = compute_temporal_risk_score(
        current,
        bl,
        ctx=_ctx(hour=14, wday=5),
        request=_req("/x"),
        db=MagicMock(),
        user_id=1,
    )
    assert raw > 0
    assert "temporal_weekday_anomaly" in reasons


def test_transition_rare(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_MIN_SAMPLES", "5")
    bl = _baseline_full()
    bl["action_transition_matrix"] = {"beneficiary_add->withdrawal": 0.01}
    current = {"total_samples_30d": 20, "activity_rate_7d": 10.0}
    req = _req("/api/v1/simulate-withdrawal")
    with patch(
        "services.auth.device_risk_temporal_engine.get_last_action_before_now",
        return_value="beneficiary_add",
    ):
        raw, reasons = compute_temporal_risk_score(
            current,
            bl,
            ctx=_ctx(),
            request=req,
            db=MagicMock(),
            user_id=1,
        )
    assert raw > 0
    assert "temporal_transition_anomaly" in reasons


def test_drift_detected(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_MIN_SAMPLES", "5")
    bl = _baseline_full()
    bl["activity_rate_ema"] = 1.0
    current = {"total_samples_30d": 30, "activity_rate_7d": 5.0}
    raw, reasons = compute_temporal_risk_score(
        current,
        bl,
        ctx=_ctx(),
        request=_req("/x"),
        db=MagicMock(),
        user_id=1,
    )
    assert raw > 0
    assert "temporal_drift_detected" in reasons


def test_apply_overlay_disabled_returns_unchanged(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_ENABLED", "false")
    reasons: list = []
    s = apply_temporal_risk_overlay(
        MagicMock(),
        user_id=1,
        request=_req("/x"),
        ctx=_ctx(),
        score_after_ml=10,
        risk_reasons=reasons,
    )
    assert s == 10


def test_f72_persist_when_score_after_ml_safe(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_WEIGHT", "1.0")
    monkeypatch.setenv("DEVICE_RISK_ML_SAFE_UPDATE_THRESHOLD", "40")

    db = MagicMock()
    db.get.return_value = None
    reasons: list = []
    snap = {
        "hour_distribution": {str(i): 1 / 24 for i in range(24)},
        "weekday_distribution": {str(i): 1 / 7 for i in range(7)},
        "action_transition_matrix": {},
        "activity_rate_7d": 1.0,
        "total_samples_30d": 15,
    }
    with patch(
        "services.auth.device_risk_temporal_engine.extract_temporal_features",
        return_value=snap,
    ):
        with patch(
            "services.auth.device_risk_temporal_engine.compute_temporal_risk_score",
            return_value=(0, []),
        ):
            with patch(
                "services.auth.device_risk_temporal_engine.persist_user_temporal_features",
            ) as m_persist:
                apply_temporal_risk_overlay(
                    db,
                    user_id=1,
                    request=_req("/x"),
                    ctx=_ctx(),
                    score_after_ml=10,
                    risk_reasons=reasons,
                )
    m_persist.assert_called_once()
    assert "temporal_ema_frozen_high_risk" not in reasons


def test_f72_ema_frozen_when_score_after_ml_high(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_TEMPORAL_WEIGHT", "1.0")
    monkeypatch.setenv("DEVICE_RISK_ML_SAFE_UPDATE_THRESHOLD", "40")

    db = MagicMock()
    db.get.return_value = None
    reasons: list = []
    snap = {
        "hour_distribution": {str(i): 1 / 24 for i in range(24)},
        "weekday_distribution": {str(i): 1 / 7 for i in range(7)},
        "action_transition_matrix": {},
        "activity_rate_7d": 1.0,
        "total_samples_30d": 15,
    }
    with patch(
        "services.auth.device_risk_temporal_engine.extract_temporal_features",
        return_value=snap,
    ):
        with patch(
            "services.auth.device_risk_temporal_engine.compute_temporal_risk_score",
            return_value=(12, ["temporal_hour_anomaly"]),
        ):
            with patch(
                "services.auth.device_risk_temporal_engine.persist_user_temporal_features",
            ) as m_persist:
                apply_temporal_risk_overlay(
                    db,
                    user_id=1,
                    request=_req("/x"),
                    ctx=_ctx(),
                    score_after_ml=55,
                    risk_reasons=reasons,
                )
    m_persist.assert_not_called()
    assert "temporal_ema_frozen_high_risk" in reasons


def test_persist_skipped_when_allow_false():
    db = MagicMock()
    persist_user_temporal_features(
        db,
        1,
        {"total_samples_30d": 1, "hour_distribution": {}, "weekday_distribution": {}, "activity_rate_7d": 0.0},
        allow_update=False,
    )
    db.add.assert_not_called()
