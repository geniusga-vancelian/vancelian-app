"""PR F.4.1 — durcissement moteur de règles dynamiques (dry-run, DSL, validation, fail-safe)."""
from __future__ import annotations

from unittest.mock import MagicMock

from services.auth.device_risk_dynamic_rules import (
    DynamicRulesEvaluationResult,
    evaluate_condition_node,
    evaluate_dynamic_rules,
    validate_risk_rule_conditions,
)
from services.auth.device_risk_engine_pr_f import RiskEvaluationContext


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


def _mock_db_rows(rows):
    db = MagicMock()
    q = MagicMock()
    chain = MagicMock()
    db.query.return_value = q
    q.filter.return_value = chain
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.all.return_value = rows
    return db


def _row(**kwargs):
    r = MagicMock()
    r.id = kwargs.get("id", "rid-1")
    r.name = kwargs.get("name", "rule")
    r.priority = kwargs.get("priority", 10)
    r.conditions = kwargs["conditions"]
    r.action = kwargs["action"]
    r.is_active = kwargs.get("is_active", True)
    r.enabled = kwargs.get("enabled", True)
    r.ruleset = kwargs.get("ruleset", "default")
    return r


def test_validate_rejects_unknown_keys():
    assert validate_risk_rule_conditions({"unknown": 1}) is False
    assert validate_risk_rule_conditions({"all": [{"bad": 1}]}) is False


def test_validate_accepts_enriched_dsl():
    assert validate_risk_rule_conditions(
        {"all": ["new_device", {"amount_gt": 10000}, {"action_type_eq": "withdrawal"}]}
    )
    assert validate_risk_rule_conditions({"country_in": ["FR", "DE"]})
    assert validate_risk_rule_conditions({"country_not_in": ["RU"]})


def test_dry_run_does_not_trigger_block(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    monkeypatch.setenv("DEVICE_RISK_RULES_DRY_RUN", "true")
    row = _row(
        name="would_block",
        conditions={"all": ["new_device"]},
        action="BLOCK",
    )
    out = evaluate_dynamic_rules(_mock_db_rows([row]), ctx=_ctx(), profile=None)
    assert isinstance(out, DynamicRulesEvaluationResult)
    assert out.outcome.triggered is False
    assert out.dry_run == {"would_trigger": "would_block", "would_action": "BLOCK"}
    assert out.explain is not None
    assert out.explain.get("rule_name") == "would_block"


def test_invalid_rule_skipped_then_match(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    monkeypatch.delenv("DEVICE_RISK_RULES_DRY_RUN", raising=False)
    bad = _row(name="bad", conditions={"oops": 1}, action="BLOCK", priority=5)
    good = _row(
        name="good",
        conditions={"all": ["new_device"]},
        action="BLOCK",
        priority=20,
    )
    out = evaluate_dynamic_rules(_mock_db_rows([bad, good]), ctx=_ctx(), profile=None)
    assert out.outcome.triggered is True
    assert out.outcome.decision == "block"
    assert "good" in (out.explain or {}).get("rule_name", "")


def test_action_type_eq_withdraw_alias_matches_withdrawal(monkeypatch):
    """Règle ``withdraw`` = alias canonique ``withdrawal`` (PR F.4.1 review)."""
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    row = _row(
        name="alias_w",
        conditions={"all": [{"action_type_eq": "withdraw"}]},
        action="STEP_UP",
    )
    ctx = _ctx(action_type="withdrawal")
    out = evaluate_dynamic_rules(_mock_db_rows([row]), ctx=ctx, profile=object())
    assert out.outcome.triggered is True
    assert out.outcome.decision == "step_up"


def test_enriched_dsl_amount_and_action(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    row = _row(
        name="high_withdrawal",
        conditions={
            "all": [
                "new_device",
                {"amount_gt": 10000},
                {"action_type_eq": "withdrawal"},
            ]
        },
        action="STEP_UP",
    )
    ctx = _ctx(amount_eur=20000.0, action_type="withdrawal")
    out = evaluate_dynamic_rules(_mock_db_rows([row]), ctx=ctx, profile=None)
    assert out.outcome.triggered is True
    assert out.outcome.decision == "step_up"
    trace = (out.explain or {}).get("matched_conditions") or []
    assert any("amount_gt" in x for x in trace)
    assert any("action_type_eq" in x for x in trace)


def test_country_in_not_in(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    r1 = _row(
        name="c_in",
        conditions={"country_in": ["DE", "AT"]},
        action="BLOCK",
        priority=1,
    )
    ctx = _ctx(current_country="DE", last_country="FR")
    assert evaluate_dynamic_rules(_mock_db_rows([r1]), ctx=ctx, profile=object()).outcome.triggered is True

    r2 = _row(
        name="c_not",
        conditions={"country_not_in": ["FR", "DE"]},
        action="BLOCK",
        priority=1,
    )
    ctx2 = _ctx(current_country="PL", last_country="FR")
    assert evaluate_dynamic_rules(_mock_db_rows([r2]), ctx=ctx2, profile=object()).outcome.triggered is True


def test_explainability_fields_on_block(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    row = _row(
        name="explain_me",
        conditions={"all": ["new_device", "country_changed"]},
        action="BLOCK",
    )
    ctx = _ctx(last_country="FR", current_country="US")
    out = evaluate_dynamic_rules(_mock_db_rows([row]), ctx=ctx, profile=None)
    assert out.explain is not None
    assert out.explain["rule_name"] == "explain_me"
    assert isinstance(out.explain["raw_conditions"], dict)
    assert out.explain["matched_conditions"]


def test_fallback_on_db_query_error(monkeypatch):
    monkeypatch.setenv("DEVICE_RISK_ENABLE_DYNAMIC_RULES", "true")
    db = MagicMock()
    db.query.side_effect = RuntimeError("db unavailable")
    out = evaluate_dynamic_rules(db, ctx=_ctx(), profile=None)
    assert out.outcome.triggered is False
    assert out.dry_run is None


def test_evaluate_condition_node_backward_compat():
    sig = {"a": True, "b": False}
    assert evaluate_condition_node({"all": ["a"]}, sig) is True
    assert evaluate_condition_node({"amount_gt": 10}, sig, ctx=None) is False
