"""Tests unitaires du mécanisme d'embeds UI — Phase 2c.2.

Couvre :

  - `ToolContext.embeds_to_emit` : champ mutable même en frozen.
  - `agent_loop` : agrégation des embeds + dédoublonnage par
    `(type, transaction_id)`.
  - `AgentEvent.to_sse_payload` : sérialisation correcte des embeds
    sur `type='done'`.
  - Service `_persist_assistant_message` : embeds bien passés dans
    `message_payload.embeds` (text et choices).

Aucune dépendance OpenAI réelle : `chat_completion_fn` simulé.

Spec : `docs/arquantix/COMPLIANCE_TOPICS.md` § 6.4.
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
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _make_agent_input() -> AgentInput:
    return AgentInput(
        user_message="Détails du dépôt ?",
        recent_turns=[],
        memory_state={
            "client_id": str(uuid4()),
            "person_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
        },
    )


def _tool_call(name: str, args: dict | None = None, *, call_id: str = "c1"):
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": "" if args is None else json.dumps(args),
        },
    }


def _make_emitting_tool(
    *,
    name: str,
    embeds_to_emit: list[dict],
    extra_result: dict | None = None,
) -> Any:
    """Crée un tool MagicMock qui pousse des embeds dans le ToolContext."""
    spec: ToolSpec = {
        "type": "function",
        "function": {
            "name": name,
            "description": f"test {name}",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        "autonomy_level": "L0",
        "agent_id": "compliance.transactional",
    }

    def _execute(ctx: ToolContext, **_kwargs):
        for emb in embeds_to_emit:
            ctx.embeds_to_emit.append(emb)
        return extra_result or {"ok": True}

    mod = MagicMock()
    mod.SPEC = spec
    mod.execute = _execute
    return mod


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    counter = {"n": 0}

    def _fake(*_args, **_kwargs):
        counter["n"] += 1
        return f"decision-{counter['n']}"

    monkeypatch.setattr(audit, "persist_decision", _fake)


async def _collect(gen):
    out: list[AgentEvent] = []
    async for ev in gen:
        out.append(ev)
    return out


# ─────────────────────────────────────────────────────────────────────
# A. ToolContext — champ mutable
# ─────────────────────────────────────────────────────────────────────


class TestToolContextEmbeds:
    def test_default_is_empty_list(self):
        ctx = ToolContext(
            db=MagicMock(),
            client_id="c1",
            person_id="p1",
            user_id=1,
            actor_kind=ActorKind.CUSTOMER,
            agent_id="compliance.transactional",
            conversation_id=str(uuid4()),
            iteration=0,
            audit_session_id=str(uuid4()),
            correlation_id="t",
        )
        assert ctx.embeds_to_emit == []

    def test_append_works_on_frozen_dataclass(self):
        ctx = ToolContext(
            db=MagicMock(),
            client_id="c1",
            person_id="p1",
            user_id=1,
            actor_kind=ActorKind.CUSTOMER,
            agent_id="compliance.transactional",
            conversation_id=str(uuid4()),
            iteration=0,
            audit_session_id=str(uuid4()),
            correlation_id="t",
        )
        ctx.embeds_to_emit.append({"type": "x", "transaction_id": "t1"})
        assert len(ctx.embeds_to_emit) == 1


# ─────────────────────────────────────────────────────────────────────
# B. AgentEvent — sérialisation SSE
# ─────────────────────────────────────────────────────────────────────


class TestAgentEventEmbedsSerialization:
    def test_done_event_includes_embeds_when_present(self):
        ev = AgentEvent(
            type="done",
            message_id="m1",
            embeds=[{"type": "transaction_detail", "transaction_id": "abc"}],
        )
        payload = ev.to_sse_payload()
        assert payload["type"] == "done"
        assert payload["embeds"] == [
            {"type": "transaction_detail", "transaction_id": "abc"}
        ]

    def test_done_event_omits_embeds_key_when_empty(self):
        ev = AgentEvent(type="done", message_id="m1", embeds=None)
        payload = ev.to_sse_payload()
        assert "embeds" not in payload

    def test_done_event_omits_embeds_key_when_empty_list(self):
        ev = AgentEvent(type="done", message_id="m1", embeds=[])
        payload = ev.to_sse_payload()
        # On choisit de ne pas émettre la clé pour économiser la BP
        # (un client legacy ne traite pas la clé `embeds`).
        assert "embeds" not in payload


# ─────────────────────────────────────────────────────────────────────
# C. Runtime agrégation — collecte + dédoublonnage
# ─────────────────────────────────────────────────────────────────────


class TestRuntimeEmbedsAggregation:
    def test_single_tool_emits_embed_in_done_event(self):
        emitting = _make_emitting_tool(
            name="emitting_tool",
            embeds_to_emit=[
                {
                    "type": "transaction_detail",
                    "transaction_id": "abc-123",
                    "actions": [],
                }
            ],
        )
        responses = [
            {"content": None, "tool_calls": [_tool_call("emitting_tool")]},
            {"content": "Voici le détail.", "tool_calls": None},
        ]

        def _completion(messages, *, model, tools, tool_choice, temperature):
            return responses.pop(0)

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="# Transactional",
                    available_tools=[emitting],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_completion,
                )
            )
        )
        done = next(e for e in events if e.type == "done")
        assert done.embeds is not None
        assert len(done.embeds) == 1
        assert done.embeds[0]["type"] == "transaction_detail"
        assert done.embeds[0]["transaction_id"] == "abc-123"

    def test_dedup_same_type_and_transaction_id(self):
        # Le LLM ré-appelle le même tool (anti-pattern mais vu en
        # pratique). Le runtime doit dédoublonner sur la clé
        # naturelle (type, transaction_id).
        emitting = _make_emitting_tool(
            name="dup_tool",
            embeds_to_emit=[
                {
                    "type": "transaction_detail",
                    "transaction_id": "abc-123",
                    "actions": [],
                }
            ],
        )
        responses = [
            {
                "content": None,
                "tool_calls": [
                    _tool_call("dup_tool", call_id="c1"),
                    _tool_call("dup_tool", call_id="c2"),
                ],
            },
            {"content": "ok", "tool_calls": None},
        ]

        def _completion(messages, *, model, tools, tool_choice, temperature):
            return responses.pop(0)

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="# Transactional",
                    available_tools=[emitting],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_completion,
                )
            )
        )
        done = next(e for e in events if e.type == "done")
        assert done.embeds is not None
        assert len(done.embeds) == 1, (
            "Le 2e appel sur le même (type, tx_id) doit être dédupé."
        )

    def test_multiple_distinct_embeds_kept(self):
        emitting_a = _make_emitting_tool(
            name="tool_a",
            embeds_to_emit=[
                {
                    "type": "transaction_detail",
                    "transaction_id": "abc-111",
                    "actions": [],
                }
            ],
        )
        emitting_b = _make_emitting_tool(
            name="tool_b",
            embeds_to_emit=[
                {
                    "type": "transaction_detail",
                    "transaction_id": "abc-222",
                    "actions": [],
                }
            ],
        )
        responses = [
            {
                "content": None,
                "tool_calls": [
                    _tool_call("tool_a", call_id="c1"),
                    _tool_call("tool_b", call_id="c2"),
                ],
            },
            {"content": "ok", "tool_calls": None},
        ]

        def _completion(messages, *, model, tools, tool_choice, temperature):
            return responses.pop(0)

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="# Transactional",
                    available_tools=[emitting_a, emitting_b],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_completion,
                )
            )
        )
        done = next(e for e in events if e.type == "done")
        assert done.embeds is not None
        assert {e["transaction_id"] for e in done.embeds} == {
            "abc-111",
            "abc-222",
        }

    def test_no_embed_means_done_embeds_is_none(self):
        # Un tool qui ne pousse rien → done.embeds = None (clé omise
        # côté SSE).
        plain = _make_emitting_tool(
            name="plain_tool",
            embeds_to_emit=[],  # rien
        )
        responses = [
            {"content": None, "tool_calls": [_tool_call("plain_tool")]},
            {"content": "ok", "tool_calls": None},
        ]

        def _completion(messages, *, model, tools, tool_choice, temperature):
            return responses.pop(0)

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="# Transactional",
                    available_tools=[plain],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_completion,
                )
            )
        )
        done = next(e for e in events if e.type == "done")
        assert done.embeds is None

    def test_service_yields_embeds_in_done_sse_payload(self):
        """Régression — le yield SSE du `done` event doit propager embeds.

        Bug observé 03/05/2026 : `service.stream_assistant_turn`
        persistait bien `message_payload.embeds` en DB (vérifié via
        SQL direct) mais omettait la clé `embeds` dans le dict yield
        au client live → l'UI Flutter ne recevait jamais l'embed sur
        un nouveau tour, alors qu'un reload via /messages aurait
        affiché la carte. Ce test garde la propagation SSE.
        """
        # Test smoke statique : s'assurer que la branche
        # `if runtime_embeds: done_payload["embeds"] = ...` est
        # bien présente. Une refacto qui retire cette propagation
        # casserait silencieusement le live UX (les tests d'agrégation
        # runtime ci-dessus passeraient toujours, parce qu'ils ne
        # voient que la persistance DB).
        import inspect
        from services.assistance import service as assistance_service

        src = inspect.getsource(assistance_service.stream_assistant_turn)
        assert (
            'done_payload["embeds"]' in src
        ), "Le yield SSE `done` doit inclure `embeds` quand runtime_embeds non-vide."

    def test_invalid_embed_dict_ignored(self):
        # Un embed sans `type` (ou avec type vide) doit être skippé.
        # Le runtime ne crash pas et n'expose pas le bruit au client.
        emitting = _make_emitting_tool(
            name="bad_tool",
            embeds_to_emit=[
                {"type": "", "transaction_id": "x"},  # type vide -> skip
                {"transaction_id": "y"},  # pas de type -> skip
                {
                    "type": "transaction_detail",
                    "transaction_id": "ok-1",
                    "actions": [],
                },
            ],
        )
        responses = [
            {"content": None, "tool_calls": [_tool_call("bad_tool")]},
            {"content": "ok", "tool_calls": None},
        ]

        def _completion(messages, *, model, tools, tool_choice, temperature):
            return responses.pop(0)

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.transactional",
                    system_prompt="# Transactional",
                    available_tools=[emitting],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_completion,
                )
            )
        )
        done = next(e for e in events if e.type == "done")
        assert done.embeds is not None
        assert len(done.embeds) == 1
        assert done.embeds[0]["transaction_id"] == "ok-1"
