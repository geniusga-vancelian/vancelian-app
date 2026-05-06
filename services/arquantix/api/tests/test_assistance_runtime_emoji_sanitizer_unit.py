"""Tests d'intégration runtime — Politique éditoriale anti-emoji.

Vérifie que ``run_agent_loop`` strip bien les emojis du delta SSE
final et expose le compteur ``emojis_stripped_count`` dans
``runtime_metrics``.

Pattern aligné sur les tests Lot 1+5 (mock chat_completion_fn).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.base import AgentEvent, AgentInput
from services.assistance.agents.runtime import run_agent_loop
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _make_agent_input(user_message: str = "Bonjour") -> AgentInput:
    return AgentInput(
        user_message=user_message,
        recent_turns=[],
        memory_state={
            "client_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
            "summarized_until_turn": None,
        },
    )


async def _collect(gen) -> list[AgentEvent]:
    return [ev async for ev in gen]


def _final_done_event(events: list[AgentEvent]) -> AgentEvent:
    done = [e for e in events if e.type == "done"]
    assert done, "expected at least one done event"
    return done[-1]


def _delta_contents(events: list[AgentEvent]) -> str:
    return "".join(e.content or "" for e in events if e.type == "delta")


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    captured: list[dict] = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return f"decision-{len(captured)}"

    monkeypatch.setattr(audit, "persist_decision", _fake)
    return captured


# ─────────────────────────────────────────────────────────────────────
# Strip dans le delta final
# ─────────────────────────────────────────────────────────────────────


class TestRuntimeEmojiStripping:
    def test_emojis_stripped_from_final_delta(self):
        """Quand le LLM produit une réponse avec des emojis, le delta
        SSE émis par le runtime ne doit PAS en contenir."""
        responses = [
            {
                "content": "Salut 👋 ! Voici une réponse 🎉 avec ✅ check.",
                "tool_calls": None,
            }
        ]
        state = {"i": 0}

        def completion(messages, *, model, tools, tool_choice, temperature):
            i = state["i"]
            state["i"] += 1
            return (
                responses[i]
                if i < len(responses)
                else {"content": "END", "tool_calls": None}
            )

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="prompt",
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

        delta_text = _delta_contents(events)
        # Les emojis ont disparu.
        for emoji in ("👋", "🎉", "✅"):
            assert emoji not in delta_text, (
                f"emoji {emoji} encore présent dans : {delta_text!r}"
            )
        # Le contenu utile reste.
        assert "Salut" in delta_text
        assert "Voici une réponse" in delta_text
        assert "check" in delta_text

    def test_emojis_stripped_count_in_runtime_metrics(self):
        responses = [
            {
                "content": "Top 🎉 ! Bien joué 💪 vraiment 🚀",
                "tool_calls": None,
            }
        ]
        state = {"i": 0}

        def completion(messages, *, model, tools, tool_choice, temperature):
            i = state["i"]
            state["i"] += 1
            return (
                responses[i]
                if i < len(responses)
                else {"content": "END", "tool_calls": None}
            )

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="prompt",
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
        done = _final_done_event(events)
        assert done.runtime_metrics is not None
        assert done.runtime_metrics["emojis_stripped_count"] == 3

    def test_clean_response_does_not_emit_metrics(self):
        """Un tour avec une réponse propre (sans emoji) ne doit pas
        polluer le payload SSE avec ``runtime_metrics`` à zéro."""
        responses = [
            {"content": "Réponse propre, sans emoji.", "tool_calls": None}
        ]
        state = {"i": 0}

        def completion(messages, *, model, tools, tool_choice, temperature):
            i = state["i"]
            state["i"] += 1
            return (
                responses[i]
                if i < len(responses)
                else {"content": "END", "tool_calls": None}
            )

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="prompt",
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
        done = _final_done_event(events)
        # runtime_metrics omis car tous les compteurs à 0.
        assert done.runtime_metrics is None

    def test_metrics_keys_include_emojis_stripped_count(self):
        """Le schéma exposé doit contenir la nouvelle clé."""
        responses = [
            {"content": "Yo 🎉", "tool_calls": None}
        ]
        state = {"i": 0}

        def completion(messages, *, model, tools, tool_choice, temperature):
            i = state["i"]
            state["i"] += 1
            return (
                responses[i]
                if i < len(responses)
                else {"content": "END", "tool_calls": None}
            )

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="prompt",
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
        done = _final_done_event(events)
        assert done.runtime_metrics is not None
        assert "emojis_stripped_count" in done.runtime_metrics
