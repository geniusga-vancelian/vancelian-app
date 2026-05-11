"""Tests — agrégateur ``conversation_state`` v1 (read-only)."""

from __future__ import annotations

import json

from services.assistance.agents.base import RouterDecision
from services.assistance.agents.conversation_state import (
    build_conversation_state,
    render_conversation_state_for_prompt,
)
from services.assistance.agents.expected_answer_scope import (
    PENDING_EXPECTATION_MEMORY_KEY,
)


class TestBuildConversationStateExpectation:
    """Scénario : réponse courte après QCM risque (user = « B »)."""

    def test_qcm_pending_expectation(self):
        scope = {
            "kind": "multiple_choice",
            "source": "agent_qcm_tool",
            "prompt_excerpt": "Quel niveau de risque acceptez-vous ?",
            "choices": [
                {"id": "A", "label": "Très prudent"},
                {"id": "B", "label": "Équilibré"},
                {"id": "C", "label": "Dynamique"},
            ],
        }
        recent = [
            {
                "role": "assistant",
                "content": "Quel niveau de risque acceptez-vous ?",
                "message_type": "choices",
                "agent_used": "advisor",
                "message_payload": {
                    "expected_answer_scope": scope,
                    "options": [
                        {"id": "A", "label": "Très prudent"},
                        {"id": "B", "label": "Équilibré"},
                    ],
                },
            },
            {"role": "user", "content": "B"},
        ]
        mem = {PENDING_EXPECTATION_MEMORY_KEY: scope}
        st = build_conversation_state(memory_state=mem, recent_turns=recent)

        assert st.expectation.expected_answer_type == "qcm_choice"
        assert st.expectation.pending_answer_expectation is True
        assert st.expectation.last_bot_question is not None
        assert len(st.expectation.last_qcm_options) == 3


class TestBuildConversationStatePendingAction:
    def test_pending_action_from_memory(self):
        mem = {
            "pending_action": {
                "action_draft_id": "abc-123",
                "action_type": "bundle_invest",
                "status": "draft",
                "target_kind": "bundle",
                "target_id": "550e8400-e29b-41d4-a716-446655440000",
                "stage": "source_list",
                "amount_from": 1000.0,
                "currency_from": "EUR",
            }
        }
        st = build_conversation_state(memory_state=mem, recent_turns=[])
        assert st.pending_action.action_draft_id == "abc-123"
        assert st.pending_action.action_type == "bundle_invest"
        assert st.pending_action.target_kind == "bundle"
        assert st.pending_action.amount_from == 1000.0
        assert st.pending_action.currency_from == "EUR"


class TestBuildConversationStateOrchestration:
    """Scénario : dépôt non reçu — intention ops + besoin transactions."""

    def test_orchestration_from_router_decision(self):
        decision = RouterDecision(
            agent_id="compliance",
            confidence=0.88,
            reasoning="",
            orchestration={
                "business_intent": "account_operations",
                "data_need": "transaction_data",
            },
        )
        st = build_conversation_state(
            memory_state={},
            recent_turns=[{"role": "user", "content": "Mon dépôt n'est pas arrivé"}],
            router_decision=decision,
        )
        assert st.orchestration.business_intent == "account_operations"
        assert st.orchestration.data_need == "transaction_data"
        assert st.orchestration.last_agent == "compliance"


class TestBuildConversationStateCognitionUx:
    """Scénario : client très tendu → pression widgets basse."""

    def test_angry_low_widget_pressure(self):
        st = build_conversation_state(
            memory_state={},
            recent_turns=[],
            cognitive_state={
                "emotional_intent": "ANGER",
                "conversation_stage": "clarification",
                "trust_level": 0.4,
                "knowledge_level": "medium",
            },
        )
        assert st.cognition.emotional_state == "angry"
        assert st.cognition.stage == "clarification"
        assert st.cognition.trust_level == "medium"
        assert st.cognition.engagement_level == "medium"
        assert st.ux.widget_pressure == "low"


class TestTopicDeriveHelpers:
    def test_topic_product_dict(self):
        st = build_conversation_state(
            memory_state={
                "current_topic": {
                    "kind": "vancelian_product",
                    "product_code": "TOP5",
                    "agent_owner": "product",
                    "set_at_turn": 4,
                    "set_by_tool": "show_bundle_detail",
                    "confidence": 0.95,
                    "set_at": "2026-05-06T12:00:00Z",
                }
            },
            recent_turns=[],
        )
        assert st.topic.active_product_id == "TOP5"
        assert st.topic.current_topic == "vancelian_product:TOP5"


class TestRenderConversationStateJson:
    def test_roundtrip_json(self):
        st = build_conversation_state(
            memory_state={},
            recent_turns=[],
            cognitive_state={"emotional_intent": "neutral"},
        )
        raw = render_conversation_state_for_prompt(st)
        parsed = json.loads(raw)
        assert "cognition" in parsed
        assert parsed["cognition"]["emotional_state"] == "neutral"
