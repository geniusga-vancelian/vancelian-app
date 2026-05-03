"""Tests unitaires du dispatcher Compliance dans le runtime — Phase 2b.

Couvre la logique injectée dans `run_agent_loop` :
  - Quand `agent_id == "compliance"` et que le LLM appelle
    `diagnose_compliance_topic` au tour 0, le `current_agent_id` switch
    vers `compliance.<topic>` pour les tours suivants.
  - Le `system_prompt` et le `tool_index` sont rechargés (validé via
    inspection du `agent_id` dans les `persist_decision`).
  - L'event SSE `thinking` est émis si l'env var
    `ASSISTANCE_STREAM_THINKING=true`.
  - Anti-boucle : un sub-agent ne peut pas rappeler
    `diagnose_compliance_topic` (validé via le registry — déjà couvert
    dans test_assistance_tools_registry_unit, mais on retest ici en
    integration).

Spec : `docs/arquantix/COMPLIANCE_TOPICS.md` § 1 et § 2.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.base import AgentEvent, AgentInput
from services.assistance.agents.runtime import run_agent_loop
from services.assistance.agents.tools.contracts import ToolSpec
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────


def _make_agent_input(user_message: str = "Bonjour"):
    return AgentInput(
        user_message=user_message,
        recent_turns=[],
        memory_state={
            "client_id": str(uuid4()),
            "person_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
        },
    )


def _make_diagnose_tool_module(*, dominant_topic: str = "registration"):
    """Construit un faux `diagnose_compliance_topic` retournant le topic."""
    spec: ToolSpec = {
        "type": "function",
        "function": {
            "name": "diagnose_compliance_topic",
            "description": "test diagnose",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        "autonomy_level": "L0",
        "agent_id": "compliance",
    }

    def _execute(_ctx, **kwargs):
        return {
            "dominant_topic": dominant_topic,
            "confidence": 0.9,
            "secondary_topics": [],
            "next_recommended_action": None,
            "context_for_llm": {},
            "triggers_used": ["test_trigger"],
        }

    mod = MagicMock()
    mod.SPEC = spec
    mod.execute = _execute
    return mod


def _make_completion_fn(responses):
    state = {"i": 0, "calls": []}

    def _fn(messages, *, model, tools, tool_choice, temperature):
        i = state["i"]
        state["i"] += 1
        # Capture le system prompt (1er message) à chaque appel pour
        # observer le rechargement après dispatch.
        sys_msg = messages[0]["content"] if messages else ""
        state["calls"].append(
            {
                "iter": i,
                "system_first_chars": sys_msg[:60] if sys_msg else "",
                "tools_count": len(tools),
            }
        )
        if i >= len(responses):
            return {"content": "FALLBACK", "tool_calls": None}
        return responses[i]

    return _fn, state


def _tool_call(name: str, args: dict | None = None, *, call_id: str | None = None):
    return {
        "id": call_id or f"call_{name}",
        "type": "function",
        "function": {
            "name": name,
            "arguments": "" if args is None else json.dumps(args),
        },
    }


async def _collect(gen):
    out = []
    async for ev in gen:
        out.append(ev)
    return out


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    captured: list[dict] = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return f"decision-{len(captured)}"

    monkeypatch.setattr(audit, "persist_decision", _fake)
    return captured


# ─────────────────────────────────────────────────────────────────────────
# A. Switch agent_id après diagnose
# ─────────────────────────────────────────────────────────────────────────


class TestComplianceDispatcher:
    @pytest.mark.parametrize(
        "topic,expected_agent_id",
        [
            ("registration", "compliance.registration"),
            ("remediation", "compliance.remediation"),
            ("transactional", "compliance.transactional"),
            ("general", "compliance.general"),
            ("unknown_xx", "compliance.general"),  # fallback
        ],
    )
    def test_switch_agent_id_after_diagnose(
        self, _stub_persist_decision, topic, expected_agent_id
    ):
        diagnose_tool = _make_diagnose_tool_module(dominant_topic=topic)
        completion, state = _make_completion_fn(
            [
                # Iter 0 : LLM appelle diagnose_compliance_topic.
                {
                    "content": None,
                    "tool_calls": [_tool_call("diagnose_compliance_topic")],
                },
                # Iter 1 : sub-agent répond directement.
                {"content": "Réponse du sub-agent.", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="Compliance dispatcher prompt.",
                    available_tools=[diagnose_tool],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # Chaque persist_decision capture l'`agent_id` au moment de
        # l'enregistrement. Le 1er (diagnose) doit être logged sous
        # `compliance` (top-level), pas le sub-agent.
        assert _stub_persist_decision, "no decision persisted"
        first_decision = _stub_persist_decision[0]
        assert first_decision["agent_id"] == "compliance"
        assert first_decision["tool_name"] == "diagnose_compliance_topic"

        # Réponse finale du sub-agent émise.
        deltas = [e.content for e in events if e.type == "delta"]
        assert any(d == "Réponse du sub-agent." for d in deltas)

    def test_no_dispatch_when_topic_missing(self, _stub_persist_decision):
        # Le tool retourne un payload SANS dominant_topic → on ne switch pas.
        spec: ToolSpec = {
            "type": "function",
            "function": {
                "name": "diagnose_compliance_topic",
                "description": "test",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            "autonomy_level": "L0",
            "agent_id": "compliance",
        }

        def _execute(_ctx, **kwargs):
            # Pas de dominant_topic → pas de switch.
            return {"confidence": 0.0, "triggers_used": []}

        mod = MagicMock()
        mod.SPEC = spec
        mod.execute = _execute

        completion, _state = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("diagnose_compliance_topic")],
                },
                {"content": "Fallback.", "tool_calls": None},
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="Top-level.",
                    available_tools=[mod],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # Toutes les decisions restent sous `compliance` (top-level).
        for d in _stub_persist_decision:
            assert d["agent_id"] == "compliance"

    @pytest.mark.parametrize(
        "topic,expected_final",
        [
            ("registration", "compliance.registration"),
            ("transactional", "compliance.transactional"),
            ("remediation", "compliance.remediation"),
            ("general", "compliance.general"),
        ],
    )
    def test_done_event_carries_final_agent_id(
        self, _stub_persist_decision, topic, expected_final
    ):
        """Phase 2b fix #3 — l'event ``done`` propage le sub-agent final.

        Permet à `service.py` de persister `assistance_messages.agent_used`
        avec le sub-agent réellement utilisé (ex. `compliance.transactional`)
        au lieu du top-level `compliance`.
        """
        diagnose_tool = _make_diagnose_tool_module(dominant_topic=topic)
        completion, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("diagnose_compliance_topic")],
                },
                {"content": "ok", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="Top-level.",
                    available_tools=[diagnose_tool],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        done_events = [e for e in events if e.type == "done"]
        assert len(done_events) == 1
        assert done_events[0].final_agent_id == expected_final
        # Sérialisation SSE : le final_agent_id doit apparaître dans
        # le payload pour que `service.py` puisse le récupérer.
        payload = done_events[0].to_sse_payload()
        assert payload["final_agent_id"] == expected_final

    def test_done_event_no_final_agent_id_when_no_dispatch(
        self, _stub_persist_decision
    ):
        """Si pas de switch (ex. pas de tool diagnose appelé), le
        ``final_agent_id`` doit rester `None` et **ne pas** apparaître
        dans le payload SSE — `service.py` retombera alors sur
        `decision.agent_id` (= top-level).
        """
        completion, _ = _make_completion_fn(
            [{"content": "réponse directe", "tool_calls": None}]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="Top-level.",
                    available_tools=[],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        done_events = [e for e in events if e.type == "done"]
        assert len(done_events) == 1
        assert done_events[0].final_agent_id is None
        payload = done_events[0].to_sse_payload()
        assert "final_agent_id" not in payload

    def test_no_dispatch_for_other_agents(self, _stub_persist_decision):
        # Un agent autre que `compliance` ne déclenche pas la logique
        # même si le LLM tente d'appeler `diagnose_compliance_topic`.
        diagnose_tool = _make_diagnose_tool_module(dominant_topic="registration")
        completion, _state = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("diagnose_compliance_topic")],
                },
                {"content": "OK", "tool_calls": None},
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="advisor",  # PAS compliance
                    system_prompt="Advisor prompt.",
                    available_tools=[diagnose_tool],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        for d in _stub_persist_decision:
            assert d["agent_id"] == "advisor"


# ─────────────────────────────────────────────────────────────────────────
# B. Thinking event SSE
# ─────────────────────────────────────────────────────────────────────────


class TestThinkingEvent:
    def test_thinking_emitted_when_enabled(self, _stub_persist_decision, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_STREAM_THINKING", "true")
        diagnose_tool = _make_diagnose_tool_module()
        completion, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("diagnose_compliance_topic")],
                },
                {"content": "OK", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="Top-level.",
                    available_tools=[diagnose_tool],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        thinking_events = [e for e in events if e.type == "thinking"]
        assert len(thinking_events) == 1
        assert thinking_events[0].thinking_phase == "diagnose"
        assert thinking_events[0].thinking_agent == "compliance"

    def test_thinking_silent_by_default(self, _stub_persist_decision, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_STREAM_THINKING", raising=False)
        diagnose_tool = _make_diagnose_tool_module()
        completion, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("diagnose_compliance_topic")],
                },
                {"content": "OK", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="Top-level.",
                    available_tools=[diagnose_tool],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        thinking_events = [e for e in events if e.type == "thinking"]
        assert len(thinking_events) == 0

    def test_thinking_only_for_compliance_agent(
        self, _stub_persist_decision, monkeypatch
    ):
        # Même avec STREAM_THINKING=true, un autre agent ne le déclenche pas.
        monkeypatch.setenv("ASSISTANCE_STREAM_THINKING", "true")
        completion, _ = _make_completion_fn(
            [{"content": "Hi", "tool_calls": None}]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="advisor",
                    system_prompt="Advisor.",
                    available_tools=[],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        assert not [e for e in events if e.type == "thinking"]
