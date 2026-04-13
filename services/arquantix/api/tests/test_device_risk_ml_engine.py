"""PR F.7 — features + score pseudo-ML."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from services.auth.device_risk_ml_engine import apply_ml_risk_overlay, compute_ml_risk_score


def test_compute_ml_risk_score_zero_when_baseline_matches():
    v = {
        "actions_per_hour": 2.0,
        "unique_devices_24h": 1.0,
        "unique_countries_24h": 1.0,
        "avg_session_duration": 100.0,
        "withdrawal_frequency": 0.5,
        "beneficiary_add_frequency": 0.1,
    }
    s, d = compute_ml_risk_score(v, dict(v))
    assert s == 0
    assert d == 0.0


def test_compute_ml_risk_score_nonzero_on_shift():
    cur = {
        "actions_per_hour": 20.0,
        "unique_devices_24h": 1.0,
        "unique_countries_24h": 1.0,
        "avg_session_duration": 100.0,
        "withdrawal_frequency": 0.5,
        "beneficiary_add_frequency": 0.1,
    }
    base = {
        "actions_per_hour": 2.0,
        "unique_devices_24h": 1.0,
        "unique_countries_24h": 1.0,
        "avg_session_duration": 100.0,
        "withdrawal_frequency": 0.5,
        "beneficiary_add_frequency": 0.1,
    }
    s, d = compute_ml_risk_score(cur, base)
    assert s > 0
    assert d > 0


@pytest.fixture
def ml_user(db):
    from tests.conftest import make_admin_user_with_pe_client

    return make_admin_user_with_pe_client(db, email="ml-f71@test.local", password="test")


def test_f71_ema_updated_when_pre_ml_score_safe(db, ml_user, monkeypatch):
    """Score PR F avant ML < seuil → persistance EMA."""
    monkeypatch.setenv("DEVICE_RISK_ML_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_ML_SAFE_UPDATE_THRESHOLD", "40")

    reasons: list = []
    with patch(
        "services.auth.device_risk_ml_engine.persist_user_risk_features",
    ) as m_persist:
        apply_ml_risk_overlay(db, user_id=ml_user.id, base_score=10, risk_reasons=reasons)
    m_persist.assert_called_once()


def test_f71_ema_frozen_when_pre_ml_score_anomalous(db, ml_user, monkeypatch):
    """Score PR F avant ML ≥ seuil → pas de mise à jour EMA (anti-poisoning)."""
    monkeypatch.setenv("DEVICE_RISK_ML_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_ML_SAFE_UPDATE_THRESHOLD", "40")

    reasons: list = []
    with patch(
        "services.auth.device_risk_ml_engine.persist_user_risk_features",
    ) as m_persist:
        apply_ml_risk_overlay(db, user_id=ml_user.id, base_score=55, risk_reasons=reasons)
    m_persist.assert_not_called()
    assert "ml_ema_frozen_high_pr_f_baseline" in reasons
