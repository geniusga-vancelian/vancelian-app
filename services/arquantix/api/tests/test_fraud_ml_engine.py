"""Tests moteur ML fraude : features, hybrid, fallback, stabilité RF."""
from __future__ import annotations

import io
import random

import pytest

from services.security.ml.fraud_feature_store import build_feature_vector
from services.security.ml.fraud_ml_model import FEATURE_KEYS
from services.security.security_response_engine import compute_global_risk_score_with_detail


def test_feature_vector_keys_and_floats(db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")
    from auth import get_password_hash
    from database import AdminUser

    u = AdminUser(email="ml_feat@test.dev", hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()
    db.refresh(u)
    fv = build_feature_vector(db, u.id)
    assert set(fv.keys()) == set(FEATURE_KEYS)
    for v in fv.values():
        assert isinstance(v, float)


def test_hybrid_scoring_formula(monkeypatch, db):
    monkeypatch.setenv("ML_WEIGHT", "0.4")
    monkeypatch.setenv("FRAUD_ML_ENFORCE_MIN_HEURISTIC", "0")
    monkeypatch.setattr(
        "services.security.security_response_engine._heuristic_risk_score",
        lambda _db, _uid: 50,
    )
    monkeypatch.setattr(
        "services.security.fraud_ml_inference_service.predict_user_risk_ml",
        lambda _db, _uid: {
            "ok": True,
            "ml_score": 100.0,
            "confidence": 0.9,
            "model_version": "test",
            "reason": "",
        },
    )
    enf, _lvl, d = compute_global_risk_score_with_detail(db, 1)
    assert d["hybrid_score"] == 70
    assert enf == 70


def test_ml_fallback_uses_heuristic_only(monkeypatch, db):
    monkeypatch.setenv("ML_WEIGHT", "0.4")
    monkeypatch.setenv("FRAUD_ML_ENFORCE_MIN_HEURISTIC", "0")
    monkeypatch.setattr(
        "services.security.security_response_engine._heuristic_risk_score",
        lambda _db, _uid: 42,
    )
    monkeypatch.setattr(
        "services.security.fraud_ml_inference_service.predict_user_risk_ml",
        lambda _db, _uid: {"ok": False, "ml_score": 0.0, "confidence": 0.0, "model_version": "", "reason": "no_model"},
    )
    enf, _lvl, d = compute_global_risk_score_with_detail(db, 1)
    assert d["hybrid_score"] == 42
    assert enf == 42


def test_enforcement_gate_blocks_ml_only_escalation(monkeypatch, db):
    monkeypatch.setenv("ML_WEIGHT", "0.4")
    monkeypatch.setenv("FRAUD_ML_ENFORCE_MIN_HEURISTIC", "45")
    monkeypatch.setattr(
        "services.security.security_response_engine._heuristic_risk_score",
        lambda _db, _uid: 20,
    )
    monkeypatch.setattr(
        "services.security.fraud_ml_inference_service.predict_user_risk_ml",
        lambda _db, _uid: {
            "ok": True,
            "ml_score": 99.0,
            "confidence": 0.99,
            "model_version": "x",
            "reason": "",
        },
    )
    enf, _lvl, d = compute_global_risk_score_with_detail(db, 1)
    assert d["hybrid_score"] > 50
    assert enf == 20


def test_random_forest_train_predict_stable(monkeypatch):
    pytest.importorskip("sklearn")
    monkeypatch.setenv("FRAUD_ML_RF_ESTIMATORS", "25")
    monkeypatch.setenv("FRAUD_ML_RF_MAX_DEPTH", "6")
    from services.security.ml.fraud_ml_model import FEATURE_KEYS, predict, train_model

    random.seed(42)
    dataset = []
    for i in range(50):
        row = {k: float(random.random() * 5 + (1 if i % 2 else 0)) for k in FEATURE_KEYS}
        dataset.append((row, i % 2))
    blob, version, extra = train_model(dataset, kind="random_forest")
    assert version
    assert extra.get("model_kind") == "random_forest"
    import joblib

    bundle = joblib.load(io.BytesIO(blob))
    fv = {k: 1.0 for k in FEATURE_KEYS}
    a = predict(fv, bundle=bundle)
    b = predict(fv, bundle=bundle)
    assert a["ok"] and b["ok"]
    assert a["ml_score"] == b["ml_score"]
    assert 0 <= a["ml_score"] <= 100
