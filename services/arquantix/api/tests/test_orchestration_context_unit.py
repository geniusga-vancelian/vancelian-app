"""Tests — normalisation orchestrateur + extraction route_to."""

from __future__ import annotations

import pytest

from services.assistance.agents.orchestration_context import (
    normalize_orchestration,
    orchestration_from_route_to_args,
    render_orchestration_for_prompt,
)


class TestNormalizeOrchestration:
    def test_none_and_empty(self):
        assert normalize_orchestration(None) is None
        assert normalize_orchestration({}) is None

    def test_coerces_invalid_enums_to_safe_defaults(self):
        out = normalize_orchestration(
            {
                "business_intent": "not_a_real_intent",
                "urgency": "extreme",
            }
        )
        assert out is not None
        assert out["business_intent"] == "general_in_scope"
        assert out["urgency"] == "medium"

    def test_secondary_intents_dedup_and_cap(self):
        out = normalize_orchestration(
            {
                "secondary_intents": [
                    "reassurance",
                    "reassurance",
                    "a",
                    "b",
                    "c",
                    "d",
                    "e",
                ],
            }
        )
        assert out is not None
        assert out["secondary_intents"] == ["reassurance", "a", "b", "c"]


class TestTransactionKind:
    def test_action_request_bundle_invest(self):
        out = normalize_orchestration(
            {
                "business_intent": "action_request",
                "transaction_kind": "bundle_invest",
            }
        )
        assert out is not None
        assert out["business_intent"] == "action_request"
        assert out["transaction_kind"] == "bundle_invest"

    def test_invalid_transaction_kind_dropped(self):
        out = normalize_orchestration(
            {
                "business_intent": "action_request",
                "transaction_kind": "exclusive_offer",
            }
        )
        assert out is not None
        assert "transaction_kind" not in out


class TestOrchestrationFromRouteToArgs:
    def test_extracts_subset(self):
        args = {
            "agent_id": "compliance",
            "confidence": 0.9,
            "reasoning": "x",
            "business_intent": "account_operations",
            "transaction_kind": "bundle_invest",
            "must_acknowledge_emotion": True,
        }
        orch = orchestration_from_route_to_args(args)
        assert orch is not None
        assert orch["business_intent"] == "account_operations"
        assert orch["transaction_kind"] == "bundle_invest"
        assert orch["must_acknowledge_emotion"] is True

    def test_no_orchestration_keys_returns_none(self):
        assert (
            orchestration_from_route_to_args(
                {"agent_id": "product", "confidence": 0.9, "reasoning": "ok"}
            )
            is None
        )


class TestRenderOrchestration:
    def test_render_non_empty(self):
        orch = normalize_orchestration(
            {"business_intent": "wealth_advice", "urgency": "low"}
        )
        text = render_orchestration_for_prompt(orch)
        assert "Décision orchestrateur" in text
        assert "wealth_advice" in text


def test_router_decision_has_optional_orchestration():
    from services.assistance.agents.base import RouterDecision

    d = RouterDecision(agent_id="default", confidence=0.0)
    assert d.orchestration is None

    d2 = RouterDecision(
        agent_id="product",
        confidence=0.9,
        orchestration={"business_intent": "product_education"},
    )
    assert d2.orchestration is not None
