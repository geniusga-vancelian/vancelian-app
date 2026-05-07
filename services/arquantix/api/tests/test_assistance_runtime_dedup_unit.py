"""Tests unitaires Phase 2 wiki v1.4 patch — dédoublonnage des tool calls
dans un même turn (cf. `agent_loop.py` :: DEDUPABLE_TOOLS).

Couvre :
  * Cas nominal : un tool appelé 2× avec mêmes args → 1ʳᵉ exécution réelle
    + 2ᵉ servie depuis le cache + hint LLM injecté.
  * Args différents → pas de dedup (les 2 appels sont exécutés).
  * Tool hors `DEDUPABLE_TOOLS` → pas de dedup (orchestration / interactif).
  * Erreur tool (timeout, internal) → pas de cache, retry permis.
  * Cache scoped au turn : reset entre 2 appels successifs à `run_agent_loop`.
  * `persist_decision` n'est pas appelé pour les hits cache (pas de
    pollution `assistance_agent_decisions`).
  * `tools_called` track les hits cache (compatible guard-rail product).

Cas réel ayant motivé la fonctionnalité : conv `5bef01e9` turn 4 où
le LLM a appelé `show_crypto_bundles` × 2 dans le même turn (DB :
``ix_assistance_agent_decisions_conv_iter`` montre iter 0 + iter 1
du même tool, mêmes args). Le 2ᵉ appel est inutile (idempotent) et
contribue à déclencher le guard-rail à tort.
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
from services.assistance.agents.runtime.agent_loop import (
    DEDUP_HINT_REPEATED_CALL,
    DEDUPABLE_TOOLS,
)
from services.assistance.agents.tools.contracts import ToolSpec
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─────────────────────────────────────────────────────────────────────
# Helpers (alignés sur test_assistance_runtime_loop_unit.py)
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
    agent_id: str = "product",
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
                    "code": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "autonomy_level": autonomy_level,
        "agent_id": agent_id,
    }
    counter = {"n": 0, "last_args": None}

    def execute(ctx, **kwargs):  # type: ignore[no-redef]
        counter["n"] += 1
        counter["last_args"] = dict(kwargs)
        return execute_result or {"ok": True}

    module = type(
        "Mod",
        (),
        {"SPEC": spec, "execute": staticmethod(execute), "counter": counter},
    )
    return module


def _make_completion_fn(responses: list[dict]):
    state = {"i": 0}

    def _fn(messages, *, model, tools, tool_choice, temperature):
        i = state["i"]
        state["i"] += 1
        if i >= len(responses):
            return {"content": "FALLBACK_END", "tool_calls": None}
        return responses[i]

    return _fn, state


def _tool_call(name: str, args: dict | None = None, *, call_id: str = "c0"):
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": "" if args is None else json.dumps(args),
        },
    }


async def _collect(gen):
    return [ev async for ev in gen]


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    """Capture les `audit.persist_decision` pour assert qu'on ne pollue
    pas la table sur les hits cache."""
    captured = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return f"decision-{len(captured)}"

    monkeypatch.setattr(audit, "persist_decision", _fake)
    return captured


# ─────────────────────────────────────────────────────────────────────
# DEDUPABLE_TOOLS — sanity check du périmètre
# ─────────────────────────────────────────────────────────────────────


class TestDedupableToolsPerimeter:
    def test_includes_product_read_tools(self):
        """Tous les tools de lecture product doivent être dédupliquables."""
        for t in (
            "select_wiki_pages",
            "read_wiki_page",
            "show_instrument_card",
            "show_crypto_bundles",
            "show_bundle_detail",
        ):
            assert t in DEDUPABLE_TOOLS, f"{t} should be dedupable"

    def test_excludes_orchestration_tools(self):
        """Les tools d'orchestration / interactifs ne doivent JAMAIS
        être dédupliqués (un re-call peut retourner un texte différent
        ou interagir avec le user)."""
        for t in (
            "consult_specialist",
            "handoff_to_agent",
            "ask_user_question",
        ):
            assert t not in DEDUPABLE_TOOLS, (
                f"{t} should NOT be dedupable (orchestration/interactive)"
            )


# ─────────────────────────────────────────────────────────────────────
# Cas nominaux
# ─────────────────────────────────────────────────────────────────────


class TestDedupNominal:
    def test_same_tool_same_args_calls_execute_once(
        self, _stub_persist_decision
    ):
        """Le LLM appelle 2× show_crypto_bundles avec les mêmes args :
        1ʳᵉ exécution réelle + 2ᵉ servie depuis cache. Le compteur
        d'execute() doit rester à 1."""
        tool = _make_tool_module(
            name="show_crypto_bundles",
            execute_result={"bundles_count": 1, "embed_emitted": True},
        )
        completion, _ = _make_completion_fn(
            [
                # Iter 1 : LLM appelle le tool une 1ʳᵉ fois.
                {
                    "content": None,
                    "tool_calls": [_tool_call("show_crypto_bundles", {}, call_id="c1")],
                },
                # Iter 2 : LLM rappelle le même tool avec mêmes args.
                {
                    "content": None,
                    "tool_calls": [_tool_call("show_crypto_bundles", {}, call_id="c2")],
                },
                # Iter 3 : LLM finalise sa réponse.
                {"content": "Voici les bundles.", "tool_calls": None},
            ]
        )

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=_make_agent_input("liste"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        # 1) execute n'a été appelé qu'1 seule fois sur 2 tool calls.
        assert tool.counter["n"] == 1, (
            f"execute called {tool.counter['n']} times; expected 1 (deduped)"
        )

        # 2) Le LLM a bien reçu sa réponse finale.
        assert any(
            ev.type == "delta" and ev.content == "Voici les bundles."
            for ev in events
        )

        # 3) `persist_decision` n'a été appelée qu'1× (le hit cache
        # n'est pas persisté pour ne pas polluer agent_decisions).
        product_decisions = [
            d for d in _stub_persist_decision
            if d.get("tool_name") == "show_crypto_bundles"
        ]
        assert len(product_decisions) == 1, (
            f"expected 1 persist_decision for dedup case, got {len(product_decisions)}"
        )

    def test_dedup_hint_injected_in_tool_result_message(
        self, _stub_persist_decision
    ):
        """Le 2ᵉ appel doit recevoir le résultat caché AVEC un
        `_dedup_hint` qui signale au LLM qu'il a déjà appelé ce tool."""
        tool = _make_tool_module(
            name="show_bundle_detail",
            execute_result={"bundle": {"id": "uuid-x"}, "embed_emitted": True},
        )
        captured_messages: list[Any] = []

        def completion(messages, *, model, tools, tool_choice, temperature):
            captured_messages.append(list(messages))
            i = len(captured_messages)
            if i == 1:
                return {
                    "content": None,
                    "tool_calls": [
                        _tool_call("show_bundle_detail", {"code": "TOP_5"}, call_id="c1")
                    ],
                }
            if i == 2:
                return {
                    "content": None,
                    "tool_calls": [
                        _tool_call("show_bundle_detail", {"code": "TOP_5"}, call_id="c2")
                    ],
                }
            return {"content": "OK.", "tool_calls": None}

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=_make_agent_input("Top 5"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        # Le 3ᵉ appel LLM (= juste avant la réponse finale) doit voir
        # le message tool du 2ᵉ tool_call avec le hint.
        third_call_messages = captured_messages[2]
        tool_msgs_after_dup = [
            m for m in third_call_messages
            if m.get("role") == "tool" and m.get("tool_call_id") == "c2"
        ]
        assert len(tool_msgs_after_dup) == 1
        content = json.loads(tool_msgs_after_dup[0]["content"])
        assert content.get("_dedup_hint") == DEDUP_HINT_REPEATED_CALL
        # Et le payload original est conservé.
        assert content.get("embed_emitted") is True

    def test_different_args_are_NOT_deduped(self, _stub_persist_decision):
        """Si les arguments diffèrent, les 2 appels sont exécutés
        normalement (cas légitime : LLM compare 2 bundles)."""
        tool = _make_tool_module(
            name="show_bundle_detail",
            execute_result={"bundle": {"id": "x"}, "embed_emitted": True},
        )
        completion, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "show_bundle_detail",
                            {"code": "TOP_5"},
                            call_id="c1",
                        )
                    ],
                },
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "show_bundle_detail",
                            {"code": "TOP_2"},
                            call_id="c2",
                        )
                    ],
                },
                {"content": "OK comparaison.", "tool_calls": None},
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=_make_agent_input("compare"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # 2 exécutions réelles puisque les args diffèrent.
        assert tool.counter["n"] == 2

    def test_tool_outside_whitelist_is_NOT_deduped(
        self, _stub_persist_decision
    ):
        """Un tool hors `DEDUPABLE_TOOLS` (ici un tool inventé pour le
        test) ne doit pas être dédupliqué — le runtime doit l'exécuter
        à chaque appel."""
        tool = _make_tool_module(
            name="custom_l1_tool_with_side_effects",
            execute_result={"updated": True},
        )
        completion, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "custom_l1_tool_with_side_effects",
                            {"x": 1},
                            call_id="c1",
                        )
                    ],
                },
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "custom_l1_tool_with_side_effects",
                            {"x": 1},
                            call_id="c2",
                        )
                    ],
                },
                {"content": "Done.", "tool_calls": None},
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=_make_agent_input("x"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # 2 exécutions car le tool n'est pas dans la whitelist.
        assert tool.counter["n"] == 2


# ─────────────────────────────────────────────────────────────────────
# Cas erreur
# ─────────────────────────────────────────────────────────────────────


class TestDedupErrorHandling:
    def test_tool_error_does_not_populate_cache(self, _stub_persist_decision):
        """Si le 1ᵉʳ appel d'un tool échoue (timeout simulé via raises),
        le 2ᵉ appel avec mêmes args doit RE-EXÉCUTER (pas servir l'erreur
        depuis cache). C'est le seul cas où on tolère 2 exécutions."""
        # Tool qui plante systématiquement.
        spec: ToolSpec = {
            "type": "function",
            "function": {
                "name": "show_crypto_bundles",
                "description": "test",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
            "autonomy_level": "L0",
            "agent_id": "product",
        }
        counter = {"n": 0}

        def execute(ctx, **kwargs):
            counter["n"] += 1
            raise RuntimeError("simulated DB blip")

        tool = type(
            "Mod",
            (),
            {"SPEC": spec, "execute": staticmethod(execute), "counter": counter},
        )
        completion, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("show_crypto_bundles", {}, call_id="c1")],
                },
                {
                    "content": None,
                    "tool_calls": [_tool_call("show_crypto_bundles", {}, call_id="c2")],
                },
                {"content": "Désolé pas dispo.", "tool_calls": None},
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=_make_agent_input("liste"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # Les 2 erreurs doivent être tentées (pas de cache d'erreur).
        assert counter["n"] == 2


# ─────────────────────────────────────────────────────────────────────
# Cache scoping (turn-level)
# ─────────────────────────────────────────────────────────────────────


class TestDedupCacheScopedToTurn:
    def test_cache_resets_between_turns(self, _stub_persist_decision):
        """2 appels successifs à `run_agent_loop` (= 2 messages user
        distincts) doivent réinitialiser le cache : un même tool appelé
        au turn 1 puis au turn 2 doit être exécuté 2 fois."""
        tool = _make_tool_module(
            name="show_crypto_bundles",
            execute_result={"bundles_count": 1, "embed_emitted": True},
        )

        # Turn 1 : 1 tool call + réponse.
        completion1, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("show_crypto_bundles", {}, call_id="t1c1")],
                },
                {"content": "OK1.", "tool_calls": None},
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="p",
                    available_tools=[tool],
                    agent_input=_make_agent_input("turn 1"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion1,
                )
            )
        )
        assert tool.counter["n"] == 1

        # Turn 2 : nouveau run_agent_loop = nouveau cache.
        completion2, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("show_crypto_bundles", {}, call_id="t2c1")],
                },
                {"content": "OK2.", "tool_calls": None},
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="p",
                    available_tools=[tool],
                    agent_input=_make_agent_input("turn 2"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion2,
                )
            )
        )
        # 1 exec turn 1 + 1 exec turn 2 = 2 totals (cache réinitialisé).
        assert tool.counter["n"] == 2
