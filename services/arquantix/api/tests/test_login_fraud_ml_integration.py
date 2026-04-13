"""Login / refresh : features fraude, évaluateur hybride, SIEM, garde-fous ML."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from database import AdminUser, AuthGlobalRiskScore, AuthSecurityEvent, AuthUserDeviceProfile


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture
def fraud_user(db):
    u = AdminUser(
        email=f"fraud_ml_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
    )
    db.add(u)
    db.flush()
    return u


def _add_login_ok(db, user_id: int, device_id: str = "d1", **meta):
    db.add(
        AuthSecurityEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            device_id=device_id[:128],
            event_type="auth.mobile_login.otp.succeeded",
            ip_address="10.0.0.1",
            user_agent=None,
            metadata_payload=dict(meta),
            created_at=_now(),
        )
    )


def test_login_feature_vector_normal_pattern(db, fraud_user, monkeypatch):
    monkeypatch.setenv("LOGIN_FRAUD_ML_EVALUATION_ENABLED", "true")
    from services.security.ml.login_fraud_features import build_login_feature_vector

    _add_login_ok(db, fraud_user.id)
    db.flush()
    fv = build_login_feature_vector(db, fraud_user.id, device_hash="ab" * 32)
    assert fv["login_count_1h"] >= 1.0
    assert fv["login_count_24h"] >= 1.0


def test_new_device_and_countries_elevates_patterns(db, fraud_user, monkeypatch):
    monkeypatch.setenv("LOGIN_FRAUD_ML_EVALUATION_ENABLED", "true")
    from services.security.ml.login_fraud_evaluator import evaluate_pattern_rules
    from services.security.ml.login_fraud_features import build_login_feature_vector

    h = "cd" * 32
    p = AuthUserDeviceProfile(
        id=uuid.uuid4(),
        user_id=fraud_user.id,
        device_hash=h[:64],
        device_id="devx",
        first_seen_at=_now() - timedelta(hours=2),
        last_seen_at=_now(),
        login_count=1,
        successful_login_count=1,
        failed_login_count=0,
        last_country="FR",
    )
    db.add(p)
    for cc, dev in [("DE", "d2"), ("ES", "d3")]:
        db.add(
            AuthSecurityEvent(
                id=uuid.uuid4(),
                user_id=fraud_user.id,
                device_id=dev,
                event_type="auth.login.succeeded",
                ip_address="10.0.1.1",
                user_agent=None,
                metadata_payload={"geo_country": cc},
                created_at=_now() - timedelta(hours=3),
            )
        )
    db.flush()
    fv = build_login_feature_vector(db, fraud_user.id, device_hash=h)
    sigs = evaluate_pattern_rules(fv)
    codes = {s["code"] for s in sigs}
    assert "new_device_multi_country_24h" in codes or "multi_device_short_window_24h" in codes


def test_evaluator_fallback_when_ml_disabled(db, fraud_user, monkeypatch):
    monkeypatch.setenv("LOGIN_FRAUD_ML_EVALUATION_ENABLED", "true")
    monkeypatch.setenv("FRAUD_ML_INFERENCE_ENABLED", "false")
    from services.security.ml.login_fraud_evaluator import evaluate_login_fraud_risk

    db.add(AuthGlobalRiskScore(user_id=fraud_user.id, score=10, level="LOW"))
    db.flush()
    out = evaluate_login_fraud_risk(db, fraud_user.id, device_hash=None, ip="10.0.0.1")
    assert out["ml_ok"] is False
    assert out["recommendation"] in ("allow", "review", "step_up", "block")


def test_ml_does_not_outrank_enforcement_guard(db, fraud_user, monkeypatch):
    monkeypatch.setenv("LOGIN_FRAUD_ML_EVALUATION_ENABLED", "true")
    monkeypatch.setenv("FRAUD_ML_INFERENCE_ENABLED", "true")
    monkeypatch.setenv("FRAUD_ML_ENFORCE_MIN_HEURISTIC", "60")
    from services.security.ml.login_fraud_evaluator import _evaluate_fraud_risk

    db.add(AuthGlobalRiskScore(user_id=fraud_user.id, score=5, level="LOW"))
    db.flush()

    with patch(
        "services.security.ml.login_fraud_evaluator.predict_user_risk_ml",
        return_value={"ok": True, "ml_score": 95.0, "confidence": 0.99, "model_version": "t"},
    ):
        with patch(
            "services.security.security_response_engine.compute_global_risk_score_with_detail",
            return_value=(5, "LOW", {"heuristic_score": 12, "enforcement_score": 12, "hybrid_score": 12}),
        ):
            out = _evaluate_fraud_risk(
                db,
                fraud_user.id,
                flow="login",
                device_hash=None,
                ip=None,
                session_id=None,
            )
    assert out["heuristic_score"] == 12
    assert out["recommendation"] != "block"
    assert out["deterministic_block_eligible"] is False


def test_siem_payload_contains_login_fraud_fields(monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "true")
    from services.security.security_event_pipeline import build_sink_payload

    payload = build_sink_payload(
        event_id="e1",
        event_type="auth.refresh.succeeded",
        user_id_db=1,
        device_id="dev",
        ip_address="10.0.0.2",
        user_agent="ua",
        metadata={
            "risk_level": "MEDIUM",
            "login_ml_score": 42.5,
            "login_ml_confidence": 0.7,
            "login_hybrid_score": 55.0,
            "login_fraud_signals": [{"code": "refresh_burst_1h", "severity": "HIGH"}],
        },
    )
    assert payload["login_ml_score"] == 42.5
    assert payload["login_hybrid_score"] == 55.0
    assert isinstance(payload["login_fraud_signals"], list)
