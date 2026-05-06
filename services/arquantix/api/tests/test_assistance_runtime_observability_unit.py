"""Tests unitaires Cognitive Bot v4 — Lot 5 « Observabilité »
(2026-05-06) — compteurs cumulés du tour exposés dans
``AgentEvent(type="done").runtime_metrics``.

Couvre :

  * ``AgentEvent.runtime_metrics`` : champ par défaut ``None``,
    sérialisation SSE intégrée.
  * ``run_agent_loop`` :
    - Tour sans tool spécial → ``runtime_metrics`` est ``None``
      (payload propre, pas de bruit pour le caller).
    - Tour avec appels wiki nominaux → ``wiki_calls_count`` exposé.
    - Tour avec quota wiki dépassé → ``wiki_quota_blocked_count`` > 0
      ET ``wiki_calls_count`` ≤ MAX (Lot 1).
    - Tour avec ``audience_filtered_out`` exposé par
      ``select_wiki_pages`` (Lot 1) → cumul exposé dans metrics.
    - Tour avec widget commercial bloqué par ``stop_pushing_active``
      (Lot 3) → ``stop_pushing_blocked_count`` > 0.
    - Sub-loop consult (chain_depth > 0) ne porte PAS de
      ``runtime_metrics`` (réservé top-level, isolation de budget).

Hors scope :
  * Logique du quota wiki (cf.
    ``test_assistance_runtime_wiki_quota_unit.py``).
  * Logique du filtre audience (cf.
    ``test_assistance_wiki_tools_unit.py``).
  * Logique du garde-fou stop_pushing (cf.
    ``test_assistance_widgets_stop_pushing_unit.py``).

Pattern de test aligné sur les tests Lot 1 (mock chat_completion_fn +
modules-tools factices).
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
from services.assistance.agents.runtime import agent_loop as agent_loop_module
from services.assistance.agents.tools.contracts import ToolSpec
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─────────────────────────────────────────────────────────────────────
# Helpers (pattern identique au test wiki_quota Lot 1)
# ─────────────────────────────────────────────────────────────────────


_QUOTA_FOR_TESTS = 2


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


def _make_tool_module(
    *,
    name: str,
    execute_result: dict | None = None,
    autonomy_level: str = "L0",
    agent_id: str = "compliance.transactional",
):
    spec: ToolSpec = {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Test tool {name}",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "category": {"type": "string"},
                    "slug": {"type": "string"},
                    "symbol": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "autonomy_level": autonomy_level,
        "agent_id": agent_id,
    }
    counter = {"n": 0}

    def execute(ctx, **kwargs):
        counter["n"] += 1
        return execute_result or {"ok": True}

    return type(
        "Mod",
        (),
        {"SPEC": spec, "execute": staticmethod(execute), "counter": counter},
    )


def _tool_call(name: str, args: dict, *, call_id: str) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(args),
        },
    }


async def _collect(gen) -> list[AgentEvent]:
    return [ev async for ev in gen]


def _final_done_event(events: list[AgentEvent]) -> AgentEvent:
    done = [e for e in events if e.type == "done"]
    assert done, "expected at least one done event"
    return done[-1]


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    captured: list[dict] = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return f"decision-{len(captured)}"

    monkeypatch.setattr(audit, "persist_decision", _fake)
    return captured


# ─────────────────────────────────────────────────────────────────────
# AgentEvent.runtime_metrics — schéma + sérialisation SSE
# ─────────────────────────────────────────────────────────────────────


class TestAgentEventRuntimeMetrics:
    def test_default_none(self):
        ev = AgentEvent(type="done")
        assert ev.runtime_metrics is None

    def test_accepts_dict(self):
        ev = AgentEvent(
            type="done",
            runtime_metrics={"wiki_calls_count": 3, "dedup_hits": 1},
        )
        assert ev.runtime_metrics == {
            "wiki_calls_count": 3,
            "dedup_hits": 1,
        }

    def test_sse_payload_omits_when_none(self):
        ev = AgentEvent(type="done", message_id="m-1")
        payload = ev.to_sse_payload()
        assert "runtime_metrics" not in payload

    def test_sse_payload_includes_when_set(self):
        ev = AgentEvent(
            type="done",
            message_id="m-1",
            runtime_metrics={"wiki_calls_count": 2},
        )
        payload = ev.to_sse_payload()
        assert payload["runtime_metrics"] == {"wiki_calls_count": 2}


# ─────────────────────────────────────────────────────────────────────
# Tour sans tool spécial → runtime_metrics None
# ─────────────────────────────────────────────────────────────────────


class TestRuntimeMetricsClean:
    def test_no_metrics_emitted_for_simple_text_only_turn(self):
        """Tour simple (LLM répond direct sans tool call) → pas de
        ``runtime_metrics`` dans le done event. Évite le bruit côté
        UX admin / logs pour les tours nominaux."""
        responses = [{"content": "Bonjour client.", "tool_calls": None}]
        state = {"i": 0}

        def completion(messages, *, model, tools, tool_choice, temperature):
            i = state["i"]
            state["i"] += 1
            return responses[i] if i < len(responses) else responses[-1]

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
        assert done.runtime_metrics is None


# ─────────────────────────────────────────────────────────────────────
# Tour avec quota wiki dépassé → wiki_quota_blocked_count > 0
# ─────────────────────────────────────────────────────────────────────


class TestRuntimeMetricsWikiQuota:
    def test_quota_blocked_count_appears_in_metrics(
        self, _stub_persist_decision, monkeypatch
    ):
        monkeypatch.setattr(
            agent_loop_module, "MAX_WIKI_CALLS_PER_TOUR", _QUOTA_FOR_TESTS
        )
        tool = _make_tool_module(
            name="read_wiki_page",
            execute_result={
                "category": "savings",
                "slug": "any",
                "audience": "client",
                "short_answer": "ok",
            },
        )

        responses: list[dict] = []
        for i in range(_QUOTA_FOR_TESTS + 2):
            responses.append({
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "read_wiki_page",
                        {"category": "savings", "slug": f"page-{i}"},
                        call_id=f"c{i}",
                    )
                ],
            })
        responses.append({"content": "Done.", "tool_calls": None})

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
                    available_tools=[tool],
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
        m = done.runtime_metrics
        assert m["wiki_calls_count"] == _QUOTA_FOR_TESTS
        assert m["wiki_quota_blocked_count"] >= 2
        # Audience filtering n'a pas été déclenché ici (compliance n'est
        # pas product mais la fiche est `client` → pas filtré).
        assert m["audience_filtered_out_total"] == 0
        assert m["stop_pushing_blocked_count"] == 0


# ─────────────────────────────────────────────────────────────────────
# Tour avec audience filtering exposé par select_wiki_pages
# ─────────────────────────────────────────────────────────────────────


class TestRuntimeMetricsAudienceFiltered:
    def test_audience_filtered_out_aggregated(
        self, _stub_persist_decision
    ):
        """``select_wiki_pages`` retourne ``audience_filtered_out: int``
        (cf. Lot 1, garde-fou audience). Le runtime doit cumuler ces
        valeurs sur tout le tour."""
        select_tool = _make_tool_module(
            name="select_wiki_pages",
            execute_result={
                "matches": [{"category": "concepts", "slug": "x"}],
                "total_returned": 1,
                "via": "keyword",
                "audience_filtered_out": 3,
            },
        )

        # 2 appels select avec args différents (pas de dedup),
        # puis finalisation.
        responses: list[dict] = [
            {
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "select_wiki_pages",
                        {"question": "q1"},
                        call_id="s1",
                    )
                ],
            },
            {
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "select_wiki_pages",
                        {"question": "q2"},
                        call_id="s2",
                    )
                ],
            },
            {"content": "Done.", "tool_calls": None},
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
                    agent_id="market",
                    system_prompt="prompt",
                    available_tools=[select_tool],
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
        m = done.runtime_metrics
        # 2 appels select * 3 fiches filtrées chacun.
        assert m["audience_filtered_out_total"] == 6
        assert m["wiki_calls_count"] == 2

    def test_audience_filtered_out_invalid_value_does_not_break(
        self, _stub_persist_decision
    ):
        """Si le tool retourne ``audience_filtered_out`` mal typé
        (str, None), on ne casse pas le tour — on ignore la valeur."""
        select_tool = _make_tool_module(
            name="select_wiki_pages",
            execute_result={
                "matches": [],
                "total_returned": 0,
                "via": "keyword",
                "audience_filtered_out": "not_an_int",  # type invalide
            },
        )
        responses = [
            {
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "select_wiki_pages",
                        {"question": "q"},
                        call_id="s1",
                    )
                ],
            },
            {"content": "Done.", "tool_calls": None},
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
                    agent_id="market",
                    system_prompt="prompt",
                    available_tools=[select_tool],
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
        # Le tour n'a pas crashé ; metrics présentes (via wiki_calls).
        assert done.runtime_metrics is not None
        # Et audience_filtered_out_total == 0 (valeur ignorée).
        assert done.runtime_metrics["audience_filtered_out_total"] == 0


# ─────────────────────────────────────────────────────────────────────
# Tour avec widget commercial bloqué par stop_pushing_active
# ─────────────────────────────────────────────────────────────────────


class TestRuntimeMetricsStopPushing:
    def test_stop_pushing_blocked_count_aggregated(
        self, _stub_persist_decision
    ):
        """Quand un widget commercial retourne
        ``error: stop_pushing_active`` (cf. Lot 3), le runtime doit
        compter le blocage dans ses métriques."""
        widget = _make_tool_module(
            name="show_instrument_card",
            execute_result={
                "error": "stop_pushing_active",
                "emotional_intent": "fear",
                "hint": "Le client est en FEAR, ne pousse pas.",
            },
        )

        responses = [
            {
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "show_instrument_card",
                        {"symbol": "BTC"},
                        call_id="w1",
                    )
                ],
            },
            {
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "show_instrument_card",
                        {"symbol": "ETH"},
                        call_id="w2",
                    )
                ],
            },
            {"content": "Done.", "tool_calls": None},
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
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[widget],
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
        assert done.runtime_metrics["stop_pushing_blocked_count"] == 2
        assert done.runtime_metrics["wiki_calls_count"] == 0


# ─────────────────────────────────────────────────────────────────────
# Cohérence : metrics snapshot ne contient que des entiers positifs
# ─────────────────────────────────────────────────────────────────────


class TestRuntimeMetricsShape:
    def test_metrics_keys_are_stable(self, _stub_persist_decision):
        """Garantit que le schéma exposé est exactement celui documenté
        — un changement de clé doit se faire en cohérence avec la doc
        et les consommateurs (admin UI, audit)."""
        widget = _make_tool_module(
            name="show_instrument_card",
            execute_result={
                "error": "stop_pushing_active",
                "emotional_intent": "fear",
                "hint": "...",
            },
        )
        responses = [
            {
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "show_instrument_card",
                        {"symbol": "BTC"},
                        call_id="w1",
                    )
                ],
            },
            {"content": "Done.", "tool_calls": None},
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
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[widget],
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
        m = done.runtime_metrics
        expected_keys = {
            "wiki_calls_count",
            "wiki_quota_blocked_count",
            "audience_filtered_out_total",
            "stop_pushing_blocked_count",
            "consultations_count",
            "embeds_count",
            "dedup_hits",
            # Politique éditoriale (2026-05-06) — emojis strippés
            # par le sanitizer post-LLM.
            "emojis_stripped_count",
        }
        assert set(m.keys()) == expected_keys
        assert all(isinstance(v, int) and v >= 0 for v in m.values())
