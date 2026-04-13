"""PR F.4 — règles dynamiques."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.auth.device_risk_engine_pr_f import RiskEvaluationContext
from services.auth.device_risk_dynamic_rules import evaluate_condition_node, evaluate_dynamic_rules
from services.security.security_env import is_device_risk_dynamic_rules_enabled


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
        current_hour_utc=12,
        weekday_utc=1,
        session_duration_sec=100.0,
        action_type="wallet_transfer",
        amount_eur=None,
    )
    d.update(kwargs)
    return RiskEvaluationContext(**d)


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", raising=False)
    assert is_device_risk_dynamic_rules_enabled() is False


def test_evaluate_all_and_any_not():
    sig = {"a": True, "b": False, "c": True}
    assert evaluate_condition_node({"all": ["a", "c"]}, sig) is True
    assert evaluate_condition_node({"all": ["a", "b"]}, sig) is False
    assert evaluate_condition_node({"any": ["b", "c"]}, sig) is True
    assert evaluate_condition_node({"not": "b"}, sig) is True
    assert evaluate_condition_node({"not": "a"}, sig) is False


def _mock_db_rows(rows):
    db = MagicMock()
    q = MagicMock()
    after_f = MagicMock()
    after_o = MagicMock()
    db.query.return_value = q
    q.filter.return_value = after_f
    after_f.order_by.return_value = after_o
    after_o.all.return_value = rows
    return db


def test_dynamic_empty_db_returns_no_trigger(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    out = evaluate_dynamic_rules(_mock_db_rows([]), ctx=_ctx(), profile=object())
    assert out.triggered is False


def test_dynamic_block_first_match(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    row = MagicMock()
    row.id = "id-1"
    row.name = "block_nc"
    row.priority = 10
    row.conditions = {"all": ["new_device", "country_changed"]}
    row.action = "BLOCK"
    row.enabled = True
    row.is_active = True
    row.ruleset = "default"

    ctx = _ctx(last_country="FR", current_country="DE")
    out = evaluate_dynamic_rules(_mock_db_rows([row]), ctx=ctx, profile=None)
    assert out.triggered is True
    assert out.decision == "block"
    assert "dynamic_rule:block_nc" in out.reasons


def test_dynamic_allow_passthrough(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    row = MagicMock()
    row.id = "id-1"
    row.name = "allow_all"
    row.priority = 5
    row.conditions = {"all": ["new_device"]}
    row.action = "ALLOW"
    row.enabled = True
    row.is_active = True
    row.ruleset = "default"

    out = evaluate_dynamic_rules(_mock_db_rows([row]), ctx=_ctx(), profile=None)
    assert out.triggered is False


def test_fallback_to_static_when_dynamic_disabled(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "false")
    db = MagicMock()
    out = evaluate_dynamic_rules(db, ctx=_ctx(), profile=None)
    assert out.triggered is False
    db.query.assert_not_called()
