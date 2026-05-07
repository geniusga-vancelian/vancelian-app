"""Scénarios « golden » légers — snapshots structuraux (conversation_state / gate)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from services.assistance.agents.base import RouterDecision
from services.assistance.agents.conversation_state import build_conversation_state
from services.assistance.agents.expected_answer_scope import (
    EXPECTED_ANSWER_SCOPE_KEY,
    PENDING_EXPECTATION_MEMORY_KEY,
)
from services.assistance.embed_gate import gate_embeds_for_ui_experience


class TestGoldenAfterQCM:
    """User « oui » avec attente liste Oui/Non précédente."""

    def test_expectation_pending_listing_choice(self):
        scope = {
            "kind": "listing_choice",
            "source": "auto_qcm",
            "choices": [
                {"ordinal": 1, "label": "Oui"},
                {"ordinal": 2, "label": "Non"},
            ],
        }
        recent = [
            {
                "role": "assistant",
                "content": "Confirmez-vous ?",
                "message_type": "text",
                "message_payload": {
                    "auto_qcm": {"prompt": "OK ?", "options": ["Oui", "Non"]},
                },
            },
            {"role": "user", "content": "oui"},
        ]
        mem = {PENDING_EXPECTATION_MEMORY_KEY: scope}
        st = build_conversation_state(memory_state=mem, recent_turns=recent)
        assert st.expectation.expected_answer_type == "listing_choice"
        assert st.expectation.pending_answer_expectation is True
        labs = [c.get("label") for c in st.expectation.last_qcm_options]
        assert "Oui" in labs


class TestGoldenProductComparison:
    """« le flexible » : option libellée contient la variante."""

    def test_choice_labels_capture_flexible(self):
        scope = {
            "kind": "multiple_choice",
            "source": "agent_qcm_tool",
            "choices": [
                {"id": "a", "label": "Profil flexible"},
                {"id": "b", "label": "Profil sécuritaire"},
            ],
        }
        recent = [
            {
                "role": "assistant",
                "content": "Quel profil ?",
                "message_type": "choices",
                "message_payload": {EXPECTED_ANSWER_SCOPE_KEY: scope, "options": []},
            },
            {"role": "user", "content": "le flexible"},
        ]
        mem: dict = {}
        st = build_conversation_state(memory_state=mem, recent_turns=recent)
        blob = "\n".join(
            str(c.get("label", "")).lower()
            for c in st.expectation.last_qcm_options
        )
        assert "flexible" in blob


class TestGoldenDepositNotReceived:
    """Bloc ops + données transaction."""

    def test_snapshot(self):
        d = RouterDecision(
            agent_id="compliance",
            confidence=0.91,
            orchestration={
                "business_intent": "account_operations",
                "data_need": "transaction_data",
            },
            cognitive_state={"emotional_intent": "neutral", "conversation_stage": "clarification"},
        )
        st = build_conversation_state(
            memory_state={"current_topic": None},
            recent_turns=[
                {"role": "assistant", "content": "Je regarde.", "agent_used": "compliance"}
            ]
            + [{"role": "user", "content": "Mon dépôt est introuvable"}],
            router_decision=d,
            cognitive_state=d.cognitive_state,
            objective={"stop_pushing": False},
        )
        dumped = st.model_dump(mode="json")
        assert dumped["orchestration"]["business_intent"] == "account_operations"
        assert dumped["orchestration"]["data_need"] == "transaction_data"


class TestGoldenAngryEmbedGate:
    """Client très tendu → embeds promo filtrés + pression UX basse."""

    def test_embed_gate_under_anger_and_stop_push(self):
        embeds = [
            {"type": "featured_articles_list"},
            {"type": "transaction_detail", "transaction_id": "t1"},
        ]
        cog = {"emotional_intent": "ANGER"}
        obj = {"stop_pushing": True}
        out = gate_embeds_for_ui_experience(embeds, cognitive_state=cog, objective=obj)
        assert len(out) == 1
        assert out[0]["type"] == "transaction_detail"
        # conversation_state ux.widget_pressure synced via build (anger → low)
        st = build_conversation_state(
            memory_state={},
            recent_turns=[
                {"role": "assistant", "message_payload": {"embeds": embeds}},
                {"role": "user", "content": "Je suis scandalisé"},
            ],
            cognitive_state=cog,
            objective=obj,
        )
        assert st.ux.widget_pressure == "low"
        assert st.cognition.emotional_state == "angry"


class TestGoldenOffTopicResume:
    """Reprise sujet : topic encore ancré + routage conseiller."""

    def test_topic_persists_for_resume(self):
        topic = {"kind": "vancelian_product", "product_code": "TOP5"}
        d = RouterDecision(
            agent_id="advisor",
            confidence=0.85,
            orchestration={
                "business_intent": "wealth_advice",
                "data_need": "none",
            },
        )
        st = build_conversation_state(
            memory_state={"current_topic": topic},
            recent_turns=[{"role": "user", "content": "Revenons à mon dossier TOP5"}],
            router_decision=d,
            cognitive_state={"conversation_stage": "discovery", "emotional_intent": "neutral"},
        )
        assert st.topic.active_product_id == "TOP5"
        assert st.orchestration.last_agent == "advisor"


def test_router_audit_wires_conversation_state(monkeypatch):
    captured: dict = {}

    def fake_persist(db, **kwargs):
        captured["arguments"] = kwargs.get("arguments", {})
        return str(uuid.uuid4())

    monkeypatch.setattr(
        "services.assistance.agents.tools.shared.audit.persist_decision",
        fake_persist,
    )
    from services.assistance.service import _persist_router_decision

    decision = RouterDecision(agent_id="product", confidence=0.92)
    _persist_router_decision(
        db=MagicMock(),
        conversation_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        decision=decision,
        conversation_state={"topic": {"current_topic": "instrument:BTC"}},
    )
    nested = captured["arguments"].get("conversation_state") or {}
    assert nested.get("topic", {}).get("current_topic") == "instrument:BTC"


def test_config_debug_flag_off_by_default(monkeypatch):
    from services.assistance import config as cfg

    monkeypatch.delenv("ASSISTANCE_CONVERSATION_STATE_DEBUG", raising=False)
    assert cfg.assistance_conversation_state_debug() is False
    monkeypatch.setenv("ASSISTANCE_CONVERSATION_STATE_DEBUG", "true")
    assert cfg.assistance_conversation_state_debug() is True
