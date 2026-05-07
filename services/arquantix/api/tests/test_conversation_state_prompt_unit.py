"""PR2 — injection ``[CONVERSATION_STATE]`` dans le prompt system des agents."""

from __future__ import annotations

import json
from types import SimpleNamespace

from services.assistance.agents.base import AgentInput
from services.assistance.agents.conversation_state import (
    CONVERSATION_STATE_MEMORY_KEY,
    build_conversation_state,
)
from services.assistance.agents.runtime.agent_loop import _build_initial_messages


def test_build_initial_messages_includes_conversation_state_block():
    """Snapshot structurel : le LLM voit le JSON agrégé sans retirer les autres blocs."""
    recent = [{"role": "user", "content": "Bonjour"}]
    decision = SimpleNamespace(
        agent_id="advisor",
        cognitive_state={
            "emotional_intent": "neutral",
            "conversation_stage": "discovery",
            "trust_level": 0.55,
            "knowledge_level": "medium",
        },
        objective={"stop_pushing": False},
        orchestration={
            "business_intent": "wealth_advice",
            "data_need": "none",
            "response_style": "educational",
            "urgency": "low",
            "regulatory_risk": "low",
        },
    )
    mem: dict = {"client_id": None, "person_id": None}
    cs = build_conversation_state(
        memory_state=mem,
        recent_turns=recent,
        router_decision=decision,
        cognitive_state=decision.cognitive_state,
        objective=decision.objective,
    )
    mem[CONVERSATION_STATE_MEMORY_KEY] = cs.model_dump(mode="json")

    agent_input = AgentInput(
        user_message="Bonjour",
        recent_turns=recent,
        memory_state=mem,
    )
    messages = _build_initial_messages(
        system_prompt="Tu es un agent test.",
        agent_input=agent_input,
    )
    assert messages[0]["role"] == "system"
    content = messages[0]["content"]
    assert "[CONVERSATION_STATE]" in content

    # JSON compact sur la ligne qui suit l’en-tête (sans parser tout le system).
    tail = content.split("[CONVERSATION_STATE]", 1)[1].strip()
    json_line = tail.split("\n", 1)[0]
    parsed = json.loads(json_line)
    assert parsed["orchestration"]["last_agent"] == "advisor"
    assert parsed["orchestration"]["business_intent"] == "wealth_advice"
    assert parsed["cognition"]["emotional_state"] == "neutral"
    assert parsed["ux"]["widget_pressure"] == "none"


def test_no_conversation_state_key_no_extra_block():
    messages = _build_initial_messages(
        system_prompt="Seul le system de base.",
        agent_input=AgentInput(
            user_message="Hi",
            recent_turns=[{"role": "user", "content": "Hi"}],
            memory_state={},
        ),
    )
    assert "[CONVERSATION_STATE]" not in messages[0]["content"]
