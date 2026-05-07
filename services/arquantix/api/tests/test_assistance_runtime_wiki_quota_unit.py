"""Tests unitaires Lot 1 « Wiki shared » (2026-05-06) — borne des appels
wiki par tour client (cf. ``agent_loop.py`` :: ``MAX_WIKI_CALLS_PER_TOUR``
et ``WIKI_TOOLS``).

Couvre :

  * Au-delà de ``MAX_WIKI_CALLS_PER_TOUR`` appels distincts à
    ``select_wiki_pages`` ou ``read_wiki_page``, le runtime court-circuite
    les calls suivants avec un tool_result d'erreur typée
    ``wiki_quota_exceeded`` + un ``hint`` exploitable par le LLM.
  * Le compteur ne s'incrémente que sur succès (un échec transient ne
    pénalise pas le budget).
  * Les tools hors ``WIKI_TOOLS`` (ex. ``show_instrument_card``) ne
    consomment pas le budget wiki.
  * La décision quota est persistée dans ``assistance_agent_decisions``
    avec ``error_code="wiki_quota_exceeded"`` pour traçabilité audit.

Pattern aligné sur ``test_assistance_runtime_dedup_unit.py``.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.base import AgentInput
from services.assistance.agents.runtime import run_agent_loop
from services.assistance.agents.runtime import agent_loop as agent_loop_module
from services.assistance.agents.runtime.agent_loop import (
    MAX_WIKI_CALLS_PER_TOUR,
    WIKI_TOOLS,
)
from services.assistance.agents.tools.contracts import ToolSpec
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# Lot 1 — `MAX_WIKI_CALLS_PER_TOUR` (6 par défaut) + le `MAX_ITER`
# runtime (6 par défaut) cohabitent. Pour ne pas saturer `MAX_ITER`
# avant que la borne wiki déclenche, on rabaisse la borne wiki à 2
# dans les tests circuit-breaker. C'est le pattern utilisé pour
# tester `MAX_CONSULTATIONS_PER_TOUR` (réécriture sur stub).
_QUOTA_FOR_TESTS = 2


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


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
    """Module-tool factice avec compteur d'appels."""
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
                    "iter": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        },
        "autonomy_level": autonomy_level,
        "agent_id": agent_id,
    }
    counter = {"n": 0, "args_log": []}

    def execute(ctx, **kwargs):
        counter["n"] += 1
        counter["args_log"].append(dict(kwargs))
        return execute_result or {"ok": True}

    module = type(
        "Mod",
        (),
        {"SPEC": spec, "execute": staticmethod(execute), "counter": counter},
    )
    return module


def _tool_call(name: str, args: dict, *, call_id: str):
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(args),
        },
    }


async def _collect(gen):
    return [ev async for ev in gen]


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    captured = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return f"decision-{len(captured)}"

    monkeypatch.setattr(audit, "persist_decision", _fake)
    return captured


# ─────────────────────────────────────────────────────────────────────
# WIKI_TOOLS — sanity check du périmètre
# ─────────────────────────────────────────────────────────────────────


class TestWikiToolsPerimeter:
    def test_perimeter_contains_select_and_read(self):
        assert "select_wiki_pages" in WIKI_TOOLS
        assert "read_wiki_page" in WIKI_TOOLS

    def test_max_wiki_calls_is_reasonable(self):
        # Sanity : pas un kill-switch (>= 4) ni un free-pass (<= 12).
        assert 4 <= MAX_WIKI_CALLS_PER_TOUR <= 12


# ─────────────────────────────────────────────────────────────────────
# Quota dépassé — court-circuit
# ─────────────────────────────────────────────────────────────────────


class TestWikiQuotaCircuitBreaker:
    def test_calls_beyond_quota_return_wiki_quota_exceeded(
        self, _stub_persist_decision, monkeypatch
    ):
        """Au (MAX+1)ᵉ appel à `read_wiki_page`, le runtime doit
        court-circuiter avec `wiki_quota_exceeded` SANS exécuter le
        tool. Le compteur d'execute s'arrête à MAX."""
        # On rabaisse la borne pour rester sous `MAX_ITER` runtime (6).
        monkeypatch.setattr(
            agent_loop_module, "MAX_WIKI_CALLS_PER_TOUR", _QUOTA_FOR_TESTS
        )
        tool = _make_tool_module(
            name="read_wiki_page",
            execute_result={
                "category": "savings",
                "slug": "any",
                "title": "Any",
                "audience": "client",
                "short_answer": "ok",
            },
        )

        # Le LLM appelle QUOTA+2 fois `read_wiki_page` avec des slugs
        # différents (donc PAS de dedup) puis finalise.
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
        captured_messages: list[Any] = []

        def completion(messages, *, model, tools, tool_choice, temperature):
            captured_messages.append(list(messages))
            i = state["i"]
            state["i"] += 1
            if i >= len(responses):
                return {"content": "FALLBACK_END", "tool_calls": None}
            return responses[i]

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=_make_agent_input("plein de questions"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        # 1) Seuls QUOTA exécutions réelles ont eu lieu.
        assert tool.counter["n"] == _QUOTA_FOR_TESTS, (
            f"expected {_QUOTA_FOR_TESTS} executions, "
            f"got {tool.counter['n']}"
        )

        # 2) La dernière itération vue par le LLM contient bien des
        # tool_results `wiki_quota_exceeded` pour les calls > QUOTA.
        last_iter_messages = captured_messages[-1]
        quota_results = []
        for m in last_iter_messages:
            if m.get("role") != "tool":
                continue
            try:
                payload = json.loads(m.get("content") or "{}")
            except json.JSONDecodeError:
                continue
            if payload.get("error") == "wiki_quota_exceeded":
                quota_results.append(payload)
        assert len(quota_results) >= 2, (
            f"expected >=2 quota_exceeded tool_results, got {len(quota_results)}"
        )
        for payload in quota_results:
            assert payload["max"] == _QUOTA_FOR_TESTS
            assert "hint" in payload

        # 3) Les `wiki_quota_exceeded` ont été persistés dans
        # `agent_decisions` avec l'error_code typé.
        quota_decisions = [
            d for d in _stub_persist_decision
            if d.get("error_code") == "wiki_quota_exceeded"
        ]
        assert len(quota_decisions) >= 2

    def test_select_wiki_pages_also_consumes_budget(
        self, _stub_persist_decision, monkeypatch
    ):
        """Le compteur agrège select_wiki_pages + read_wiki_page —
        un mix des deux dépasse le budget identiquement."""
        monkeypatch.setattr(
            agent_loop_module, "MAX_WIKI_CALLS_PER_TOUR", _QUOTA_FOR_TESTS
        )
        select_tool = _make_tool_module(
            name="select_wiki_pages",
            execute_result={
                "matches": [{"category": "savings", "slug": "x"}],
                "total_returned": 1,
                "via": "keyword",
            },
        )
        read_tool = _make_tool_module(
            name="read_wiki_page",
            execute_result={
                "category": "savings",
                "slug": "x",
                "audience": "client",
                "short_answer": "ok",
            },
        )

        responses: list[dict] = []
        # QUOTA appels: alternance select/read avec args distincts
        # pour éviter le dedup.
        for i in range(_QUOTA_FOR_TESTS):
            if i % 2 == 0:
                responses.append({
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "select_wiki_pages",
                            {"question": f"q{i}"},
                            call_id=f"s{i}",
                        )
                    ],
                })
            else:
                responses.append({
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "read_wiki_page",
                            {"category": "savings", "slug": f"slug-{i}"},
                            call_id=f"r{i}",
                        )
                    ],
                })
        # +1 appel qui doit être bloqué.
        responses.append({
            "content": None,
            "tool_calls": [
                _tool_call(
                    "select_wiki_pages",
                    {"question": "extra"},
                    call_id="extra",
                )
            ],
        })
        responses.append({"content": "Done.", "tool_calls": None})

        state = {"i": 0}

        def completion(messages, *, model, tools, tool_choice, temperature):
            i = state["i"]
            state["i"] += 1
            if i >= len(responses):
                return {"content": "FALLBACK_END", "tool_calls": None}
            return responses[i]

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="advisor",
                    system_prompt="prompt",
                    available_tools=[select_tool, read_tool],
                    agent_input=_make_agent_input("mix"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        # QUOTA appels exécutés en cumul (select + read).
        total_executed = (
            select_tool.counter["n"] + read_tool.counter["n"]
        )
        assert total_executed == _QUOTA_FOR_TESTS

        # L'appel "extra" a été bloqué → persist_decision a un
        # `wiki_quota_exceeded`.
        quota_decisions = [
            d for d in _stub_persist_decision
            if d.get("error_code") == "wiki_quota_exceeded"
        ]
        assert len(quota_decisions) >= 1


# ─────────────────────────────────────────────────────────────────────
# Quota — non-régression sur tools hors WIKI_TOOLS
# ─────────────────────────────────────────────────────────────────────


class TestWikiQuotaIsolation:
    def test_non_wiki_tool_does_not_consume_budget(
        self, _stub_persist_decision, monkeypatch
    ):
        """Un tool hors `WIKI_TOOLS` (ex. `show_instrument_card`)
        peut être appelé QUOTA+1 fois sans déclencher la borne wiki."""
        monkeypatch.setattr(
            agent_loop_module, "MAX_WIKI_CALLS_PER_TOUR", _QUOTA_FOR_TESTS
        )
        non_wiki_tool = _make_tool_module(
            name="show_instrument_card",
            execute_result={"symbol": "BTC", "embed_emitted": True},
        )

        responses: list[dict] = []
        for i in range(_QUOTA_FOR_TESTS + 1):
            responses.append({
                "content": None,
                "tool_calls": [
                    _tool_call(
                        "show_instrument_card",
                        {"symbol": f"SYM{i}"},
                        call_id=f"c{i}",
                    )
                ],
            })
        responses.append({"content": "Done.", "tool_calls": None})

        state = {"i": 0}

        def completion(messages, *, model, tools, tool_choice, temperature):
            i = state["i"]
            state["i"] += 1
            if i >= len(responses):
                return {"content": "FALLBACK_END", "tool_calls": None}
            return responses[i]

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[non_wiki_tool],
                    agent_input=_make_agent_input("plein"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        # Le tool tourne pour les QUOTA+1 appels (sans throttle wiki).
        assert non_wiki_tool.counter["n"] >= _QUOTA_FOR_TESTS + 1, (
            f"non-wiki tool was throttled: {non_wiki_tool.counter['n']} "
            f"executions"
        )

        # Aucune décision `wiki_quota_exceeded` enregistrée.
        quota_decisions = [
            d for d in _stub_persist_decision
            if d.get("error_code") == "wiki_quota_exceeded"
        ]
        assert quota_decisions == []
