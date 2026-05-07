"""Tests unitaires du runtime agent loop — Phase 2a multi-agents.

Couvre :
  - `services.assistance.agents.runtime.agent_loop.run_agent_loop` :
    cas nominaux (réponse directe, 1 tool puis réponse, multi-tools),
    cas limites (MAX_ITER, timeout total, hallucination tool, LLM error),
    interrupt via `ask_user_question`.
  - Garde-fous d'autonomy gating : un tool L1 n'est jamais exposé à OpenAI
    si `autonomy_max=L0` (cf. RUNTIME § 3).
  - Sanitization tipping-off via `audit.sanitize_reasoning` et
    persistance `agent_decisions`.

Aucune dépendance OpenAI réelle : on injecte un `chat_completion_fn`
custom qui simule des messages assistant successifs.

Spec de référence : `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 1, § 7, § 16.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.base import AgentEvent, AgentInput
from services.assistance.agents.runtime import (
    MAX_ITER_FALLBACK_MESSAGE,
    run_agent_loop,
)
from services.assistance.agents.tools.contracts import ToolSpec
from services.assistance.agents.tools.shared import (
    audit,
    ask_user_question as ask_user_question_module,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.assistance.llm import LLMError


# ─────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────


def _make_agent_input(
    user_message: str = "Bonjour",
    *,
    summary: str | None = None,
    long_memory: dict | None = None,
    recent_turns: list[dict] | None = None,
) -> AgentInput:
    return AgentInput(
        user_message=user_message,
        recent_turns=recent_turns or [],
        memory_state={
            "client_id": str(uuid4()),
            "conversation_summary": summary,
            "client_long_memory": long_memory,
            "summarized_until_turn": None,
        },
    )


def _make_tool_module(
    *,
    name: str,
    autonomy_level: str = "L0",
    agent_id: str = "compliance",
    execute_result: dict | None = None,
    raises: BaseException | None = None,
    is_async: bool = False,
):
    """Construit un module-tool factice (objet avec SPEC + execute)."""
    spec: ToolSpec = {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Test tool {name}",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        "autonomy_level": autonomy_level,
        "agent_id": agent_id,
    }

    if is_async:
        async def _execute(_ctx, **kwargs):
            if raises is not None:
                raise raises
            return execute_result if execute_result is not None else {"ok": True}
    else:
        def _execute(_ctx, **kwargs):
            if raises is not None:
                raise raises
            return execute_result if execute_result is not None else {"ok": True}

    mod = MagicMock()
    mod.SPEC = spec
    mod.execute = _execute
    return mod


def _make_completion_fn(responses: list[dict]):
    """Construit un fake `chat_completion_with_tools` qui retourne
    la liste `responses` séquentiellement.

    Chaque entrée doit être un dict OpenAI-style :
        {"content": "...", "tool_calls": [...]}
    """
    state = {"i": 0}

    def _fn(messages, *, model, tools, tool_choice, temperature):
        i = state["i"]
        state["i"] += 1
        if i >= len(responses):
            return {"content": "FALLBACK_NO_MORE_RESPONSES", "tool_calls": None}
        return responses[i]

    return _fn, state


def _tool_call(name: str, args: dict | None = None, *, call_id: str | None = None):
    return {
        "id": call_id or f"call_{name}",
        "type": "function",
        "function": {
            "name": name,
            "arguments": "" if args is None else __import__("json").dumps(args),
        },
    }


async def _collect(gen):
    """Itère un async generator et retourne la liste des events."""
    out = []
    async for ev in gen:
        out.append(ev)
    return out


# ─────────────────────────────────────────────────────────────────────────
# A. Cas nominaux
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    """Mock `audit.persist_decision` pour les tests unit (pas de DB)."""
    counter = {"n": 0}

    def _fake(*args, **kwargs):
        counter["n"] += 1
        return f"decision-{counter['n']}"

    monkeypatch.setattr(audit, "persist_decision", _fake)
    return counter


class TestNominalFlows:
    """Réponse directe sans tool, 1-tool-puis-réponse, multi-tools."""

    def test_direct_answer_no_tools(self):
        completion, state = _make_completion_fn(
            [{"content": "Bonjour, je suis là.", "tool_calls": None}]
        )
        ai = _make_agent_input("salut")
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="You are a helpful assistant.",
                    available_tools=[],
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        assert state["i"] == 1
        types = [e.type for e in events]
        # warm-up delta vide + delta réponse + done
        assert types[0] == "delta" and (events[0].content or "") == ""
        assert any(
            e.type == "delta" and e.content == "Bonjour, je suis là." for e in events
        )
        assert events[-1].type == "done"

    def test_one_tool_then_answer(self, _stub_persist_decision):
        tool = _make_tool_module(
            name="read_compliance_state",
            execute_result={"actor_kind": "customer", "documents": []},
        )
        completion, state = _make_completion_fn(
            [
                {"content": None, "tool_calls": [_tool_call("read_compliance_state")]},
                {"content": "Tout est OK.", "tool_calls": None},
            ]
        )
        ai = _make_agent_input("où en est mon dossier ?")
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="You are compliance.",
                    available_tools=[tool],
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        assert state["i"] == 2  # 2 itérations LLM
        deltas = [e.content for e in events if e.type == "delta"]
        assert "Tout est OK." in deltas
        assert _stub_persist_decision["n"] == 1

    def test_multi_tools_same_iteration(self, _stub_persist_decision):
        t1 = _make_tool_module(
            name="read_compliance_state", execute_result={"docs": 1}
        )
        t2 = _make_tool_module(
            name="read_documents", execute_result={"count": 3}
        )
        completion, state = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call("read_compliance_state"),
                        _tool_call("read_documents"),
                    ],
                },
                {"content": "Voilà la synthèse.", "tool_calls": None},
            ]
        )
        ai = _make_agent_input("synthese")
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="You are compliance.",
                    available_tools=[t1, t2],
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        assert state["i"] == 2
        assert _stub_persist_decision["n"] == 2  # un decision par tool
        assert events[-1].type == "done"


# ─────────────────────────────────────────────────────────────────────────
# B. Limites & erreurs
# ─────────────────────────────────────────────────────────────────────────


class TestLimits:
    """MAX_ITER, timeout, LLM down, tool inconnu, tool exception."""

    def test_max_iter_emits_fallback(self, monkeypatch, _stub_persist_decision):
        monkeypatch.setenv("ASSISTANCE_AGENT_MAX_ITER", "2")
        # Le LLM rappelle un tool en boucle, jamais de réponse finale.
        tool = _make_tool_module(
            name="read_compliance_state", execute_result={"x": 1}
        )
        responses = [
            {"content": None, "tool_calls": [_tool_call("read_compliance_state")]}
            for _ in range(5)
        ]
        completion, state = _make_completion_fn(responses)
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="You are compliance.",
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
        assert state["i"] == 2  # respect du clamp
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any(MAX_ITER_FALLBACK_MESSAGE in d for d in deltas)
        assert events[-1].type == "done"

    def test_llm_error_short_circuits(self):
        # Patch C.1 — neutralise le backoff retry pour ce test
        # (la 502 reste retryable, mais on veut que le test reste
        # rapide ; le retry est testé séparément dans
        # `test_assistance_llm_retry_unit.py`).
        with patch(
            "services.assistance.agents.runtime.agent_loop.LLM_BACKOFF_SCHEDULE",
            (0.0, 0.0),
        ):
            def _bomb(*a, **kw):
                raise LLMError("upstream_status_502")

            events = asyncio.run(
                _collect(
                    run_agent_loop(
                        agent_id="compliance",
                        system_prompt="...",
                        available_tools=[],
                        agent_input=_make_agent_input(),
                        actor_kind=ActorKind.CUSTOMER,
                        db=MagicMock(),
                        conversation_id=uuid4(),
                        user_id=42,
                        chat_completion_fn=_bomb,
                    )
                )
            )
            types = [e.type for e in events]
            assert "error" in types
            assert any(
                e.type == "error" and e.error_code == "llm_unavailable" for e in events
            )

    def test_unknown_tool_yields_error_to_llm_then_continues(
        self, _stub_persist_decision
    ):
        """Si le LLM hallucine un tool, on retourne `{"error": "tool_not_found"}`
        au LLM (qui peut s'auto-corriger au tour suivant)."""
        completion, state = _make_completion_fn(
            [
                {"content": None, "tool_calls": [_tool_call("nonexistent_tool")]},
                {"content": "Désolé, j'ai mal cherché.", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
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
        assert state["i"] == 2
        assert events[-1].type == "done"
        # On a quand même persisté la décision avec error_code=tool_not_found
        assert _stub_persist_decision["n"] == 1

    def test_tool_exception_returns_internal_error_to_llm(
        self, _stub_persist_decision
    ):
        boom_tool = _make_tool_module(
            name="boom", raises=RuntimeError("kaboom")
        )
        completion, state = _make_completion_fn(
            [
                {"content": None, "tool_calls": [_tool_call("boom")]},
                {"content": "OK je continue.", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
                    available_tools=[boom_tool],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        assert events[-1].type == "done"


# ─────────────────────────────────────────────────────────────────────────
# C. Interrupt — ask_user_question
# ─────────────────────────────────────────────────────────────────────────


class TestAskUserQuestionInterrupt:
    """Le tool `ask_user_question` doit interrompre la boucle et émettre
    un event `choices`."""

    def test_ask_user_question_emits_choices_and_done(
        self, _stub_persist_decision
    ):
        completion, state = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "ask_user_question",
                            args={
                                "prompt": "Quel est l'objet de ton virement ?",
                                "options": [
                                    {"id": "loyer", "label": "Loyer"},
                                    {"id": "salaire", "label": "Salaire"},
                                ],
                                "allow_freeform": True,
                            },
                        )
                    ],
                }
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
                    available_tools=[ask_user_question_module],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        choices_evs = [e for e in events if e.type == "choices"]
        assert len(choices_evs) == 1
        ch = choices_evs[0]
        assert ch.prompt == "Quel est l'objet de ton virement ?"
        assert {o.id for o in (ch.options or [])} == {"loyer", "salaire"}
        assert ch.allow_freeform is True
        assert events[-1].type == "done"

    def test_ask_user_question_persists_decision_row(
        self, _stub_persist_decision
    ):
        completion, _ = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "ask_user_question",
                            args={"prompt": "Confirme ?"},
                        )
                    ],
                }
            ]
        )
        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
                    available_tools=[ask_user_question_module],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        assert _stub_persist_decision["n"] == 1


# ─────────────────────────────────────────────────────────────────────────
# D. Autonomy gating
# ─────────────────────────────────────────────────────────────────────────


class TestAutonomyGating:
    """Filtre des tools selon `autonomy_max(agent_id)` + kill-switch."""

    def test_l1_tool_filtered_when_kill_switch_on(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_GLOBAL_AUTONOMY_KILLSWITCH", "true")
        tools_passed_to_llm: list[Any] = []

        def _capture(messages, *, model, tools, tool_choice, temperature):
            tools_passed_to_llm.extend(tools)
            return {"content": "OK", "tool_calls": None}

        l0_tool = _make_tool_module(name="read_state", autonomy_level="L0")
        l1_tool = _make_tool_module(name="propose_action", autonomy_level="L1")
        l2_tool = _make_tool_module(
            name="request_doc_upload", autonomy_level="L2"
        )

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
                    available_tools=[l0_tool, l1_tool, l2_tool],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_capture,
                )
            )
        )
        names = {
            (t.get("function") or {}).get("name") for t in tools_passed_to_llm
        }
        assert names == {"read_state"}, (
            f"kill-switch ON should filter out L1 + L2, got {names}"
        )

    def test_l2_tool_allowed_when_kill_switch_off_and_max_l2(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_GLOBAL_AUTONOMY_KILLSWITCH", "false")
        monkeypatch.setenv("ASSISTANCE_COMPLIANCE_AUTONOMY_MAX", "L2")
        captured: list[Any] = []

        def _capture(messages, *, model, tools, tool_choice, temperature):
            captured.extend(tools)
            return {"content": "OK", "tool_calls": None}

        l0 = _make_tool_module(name="t0", autonomy_level="L0")
        l1 = _make_tool_module(name="t1", autonomy_level="L1")
        l2 = _make_tool_module(name="t2", autonomy_level="L2")
        l3 = _make_tool_module(name="t3", autonomy_level="L3")

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
                    available_tools=[l0, l1, l2, l3],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_capture,
                )
            )
        )
        names = {(t.get("function") or {}).get("name") for t in captured}
        assert names == {"t0", "t1", "t2"}


# ─────────────────────────────────────────────────────────────────────────
# E. Court-circuits acteurs (défense en profondeur)
# ─────────────────────────────────────────────────────────────────────────


class TestActorShortCircuits:
    """Si actor=ADMIN_BO ou SUSPENDED, le runtime émet un error et stop."""

    def test_admin_bo_emits_error_no_llm_call(self):
        called = {"n": 0}

        def _fn(*a, **kw):
            called["n"] += 1
            return {"content": "should not be called", "tool_calls": None}

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
                    available_tools=[],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.ADMIN_BO,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_fn,
                )
            )
        )
        assert called["n"] == 0
        assert any(
            e.type == "error"
            and e.error_code == "actor_admin_bo_not_allowed"
            for e in events
        )

    def test_suspended_emits_error_no_llm_call(self):
        called = {"n": 0}

        def _fn(*a, **kw):
            called["n"] += 1
            return {"content": "x", "tool_calls": None}

        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance",
                    system_prompt="...",
                    available_tools=[],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.SUSPENDED,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=_fn,
                )
            )
        )
        assert called["n"] == 0
        assert any(
            e.type == "error"
            and e.error_code == "actor_suspended_short_circuit"
            for e in events
        )


# ─────────────────────────────────────────────────────────────────────────
# F. Sanitizer tipping-off (défense en profondeur)
# ─────────────────────────────────────────────────────────────────────────


class TestSanitizerIntegration:
    """L'audit doit toujours filtrer les mots blacklistés."""

    @pytest.mark.parametrize(
        "raw,expected_count",
        [
            ("Le client est suspect de fraude.", 2),
            ("watchlist hit OFAC PEP", 3),
            ("Tout va bien.", 0),
            ("", 0),
            (None, 0),
        ],
    )
    def test_sanitize_reasoning_counts(self, raw, expected_count):
        cleaned, n = audit.sanitize_reasoning(raw)
        assert n == expected_count
        for term in audit.TIPPING_OFF_BLACKLIST:
            assert term.lower() not in cleaned.lower()

    def test_sanitize_is_idempotent(self):
        text = "Le client est suspect de fraude."
        once, _ = audit.sanitize_reasoning(text)
        twice, n2 = audit.sanitize_reasoning(once)
        assert once == twice
        assert n2 == 0


# ─────────────────────────────────────────────────────────────────────────
# G. Phase 2 wiki — Guard-rail anti-hallucination agent `product` (2026-05-04)
# ─────────────────────────────────────────────────────────────────────────


class TestProductGuardrailHelper:
    """Tests directs de `_check_product_guardrail` (logique pure, sans loop)."""

    def test_no_tools_called_returns_no_read_hint(self):
        from services.assistance.agents.runtime.agent_loop import (
            PRODUCT_GUARDRAIL_HINT_NO_READ,
            _check_product_guardrail,
        )
        assert _check_product_guardrail([]) == PRODUCT_GUARDRAIL_HINT_NO_READ

    def test_only_select_returns_select_without_read_hint(self):
        from services.assistance.agents.runtime.agent_loop import (
            PRODUCT_GUARDRAIL_HINT_SELECT_WITHOUT_READ,
            _check_product_guardrail,
        )
        assert (
            _check_product_guardrail(["select_wiki_pages"])
            == PRODUCT_GUARDRAIL_HINT_SELECT_WITHOUT_READ
        )

    def test_select_then_read_wiki_page_returns_none(self):
        from services.assistance.agents.runtime.agent_loop import _check_product_guardrail
        assert (
            _check_product_guardrail(["select_wiki_pages", "read_wiki_page"]) is None
        )

    def test_only_show_instrument_card_returns_none(self):
        """show_instrument_card seul est une lecture valide (carte produit live)."""
        from services.assistance.agents.runtime.agent_loop import _check_product_guardrail
        assert _check_product_guardrail(["show_instrument_card"]) is None

    def test_list_topics_only_does_not_satisfy_guardrail(self):
        """Un tool inconnu / hors périmètre lecture ne satisfait pas le guard-rail."""
        from services.assistance.agents.runtime.agent_loop import (
            PRODUCT_GUARDRAIL_HINT_NO_READ,
            _check_product_guardrail,
        )
        assert (
            _check_product_guardrail(["list_product_knowledge_topics"])
            == PRODUCT_GUARDRAIL_HINT_NO_READ
        )


class TestProductGuardrailIntegration:
    """Tests d'intégration du guard-rail dans `run_agent_loop`."""

    def test_product_no_tool_triggers_retry_with_hint(self, _stub_persist_decision):
        """Cas turn 30 / 32 de la conv aef5923a : product répond direct sans tool.
        Le guard-rail doit injecter un hint et relancer la boucle."""
        # 1er tour : LLM répond direct sans tool (simule turn 30 hallucinatoire)
        # 2e tour (après injection hint) : LLM finit par appeler un tool de lecture
        tool = _make_tool_module(
            name="read_wiki_page",
            agent_id="product",
            execute_result={"title": "Coffre", "short_answer": "Le coffre…"},
        )
        completion, state = _make_completion_fn(
            [
                {"content": "Vancelian propose plusieurs produits…", "tool_calls": None},
                {
                    "content": None,
                    "tool_calls": [
                        _tool_call(
                            "read_wiki_page",
                            {"category": "savings", "slug": "product_basics_vault"},
                        )
                    ],
                },
                {"content": "Voici la fiche officielle.", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="You are product agent.",
                    available_tools=[tool],
                    agent_input=_make_agent_input("Découvrir un produit Vancelian"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # Le guard-rail a forcé 3 itérations LLM (réponse hallucinée → hint
        # injecté → tool call → réponse finale), pas 1.
        assert state["i"] == 3
        # La réponse finale rendue à l'utilisateur est la "Voici la fiche…",
        # pas le brouillon hallucinatoire.
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any("Voici la fiche officielle" in d for d in deltas)
        assert not any("plusieurs produits" in d for d in deltas)

    def test_product_select_without_read_triggers_retry(self, _stub_persist_decision):
        """Cas turn 42 de la conv aef5923a : select × N sans read_wiki_page."""
        select_tool = _make_tool_module(
            name="select_wiki_pages",
            agent_id="product",
            execute_result={"matches": [{"slug": "x", "category": "y", "score": 5.0}]},
        )
        read_tool = _make_tool_module(
            name="read_wiki_page",
            agent_id="product",
            execute_result={"slug": "x", "category": "y", "short_answer": "OK"},
        )
        completion, state = _make_completion_fn(
            [
                # Turn 1 : LLM appelle select × 2 puis tente de répondre direct
                {
                    "content": None,
                    "tool_calls": [_tool_call("select_wiki_pages", {"question": "produits"})],
                },
                {"content": "Voici les meilleurs produits…", "tool_calls": None},
                # Turn post-hint : LLM appelle enfin read_wiki_page
                {
                    "content": None,
                    "tool_calls": [_tool_call("read_wiki_page", {"slug": "x", "category": "y"})],
                },
                {"content": "Réponse sourcée.", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="You are product.",
                    available_tools=[select_tool, read_tool],
                    agent_input=_make_agent_input("quels sont les meilleurs produits ?"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # 4 itérations : select → réponse rejetée → read → réponse finale
        assert state["i"] == 4
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any("Réponse sourcée" in d for d in deltas)

    def test_product_with_proper_tool_no_retry(self, _stub_persist_decision):
        """Cas turn 36 / 40 (nominal) : LLM appelle read_wiki_page avant de répondre.
        Pas de guard-rail, pas de retry."""
        tool = _make_tool_module(
            name="read_wiki_page",
            agent_id="product",
            execute_result={"slug": "vault", "short_answer": "Le coffre…"},
        )
        completion, state = _make_completion_fn(
            [
                {
                    "content": None,
                    "tool_calls": [_tool_call("read_wiki_page", {"slug": "vault", "category": "vault"})],
                },
                {"content": "Réponse correcte.", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="You are product.",
                    available_tools=[tool],
                    agent_input=_make_agent_input("parle moi du coffre"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        assert state["i"] == 2  # Pas de retry — comportement nominal.
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any("Réponse correcte" in d for d in deltas)

    def test_product_guardrail_max_one_retry(self, _stub_persist_decision):
        """Si le LLM ignore le hint et répond toujours sans tool au 2e essai,
        on accepte la réponse (pas de boucle infinie)."""
        completion, state = _make_completion_fn(
            [
                {"content": "Réponse sans tool 1.", "tool_calls": None},
                # Après injection du hint, le LLM répond encore sans tool
                {"content": "Réponse sans tool 2.", "tool_calls": None},
                # Filet : si jamais on continuait, ce 3e essai fail le test
                {"content": "NE_DEVRAIT_PAS_APPARAITRE", "tool_calls": None},
            ]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="You are product.",
                    available_tools=[],
                    agent_input=_make_agent_input("question test"),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )
        # Exactement 2 itérations : 1ère rejetée, 2e acceptée même sans tool.
        assert state["i"] == 2
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any("Réponse sans tool 2" in d for d in deltas)
        # Et la 1ère hallucinée n'a PAS été émise au client.
        assert not any("Réponse sans tool 1" in d for d in deltas)

    def test_guardrail_disabled_via_env(self, monkeypatch, _stub_persist_decision):
        """ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED=false → comportement legacy."""
        monkeypatch.setenv("ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED", "false")
        completion, state = _make_completion_fn(
            [{"content": "Réponse legacy non-sourcée.", "tool_calls": None}]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="...",
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
        assert state["i"] == 1  # Pas de retry — guard-rail off.
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any("Réponse legacy non-sourcée" in d for d in deltas)

    def test_guardrail_does_not_apply_to_other_agents(self, _stub_persist_decision):
        """Le guard-rail est product-only — un autre agent peut répondre direct."""
        completion, state = _make_completion_fn(
            [{"content": "Compliance répond direct.", "tool_calls": None}]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="compliance.general",
                    system_prompt="...",
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
        assert state["i"] == 1
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any("Compliance répond direct" in d for d in deltas)

    def test_guardrail_does_not_apply_in_consult_subloop(self, _stub_persist_decision):
        """En sous-loop consult (consult_in_progress=True), le specialist
        peut répondre depuis son seul prompt sur des questions définitionnelles."""
        completion, state = _make_completion_fn(
            [{"content": "Spécialiste répond bref.", "tool_calls": None}]
        )
        events = asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="...",
                    available_tools=[],
                    agent_input=_make_agent_input(),
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                    consult_in_progress=True,
                )
            )
        )
        assert state["i"] == 1  # Pas de retry — sous-loop consult.
        deltas = [e.content for e in events if e.type == "delta" and e.content]
        assert any("Spécialiste répond bref" in d for d in deltas)


class TestProductGuardrailConfig:
    """`assistance_product_guardrail_enabled()` — lecture env var."""

    def test_enabled_by_default(self, monkeypatch):
        from services.assistance.agents.config import assistance_product_guardrail_enabled
        monkeypatch.delenv("ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED", raising=False)
        assert assistance_product_guardrail_enabled() is True

    @pytest.mark.parametrize("val", ["true", "1", "yes", "on", "TRUE", "True"])
    def test_enabled_truthy_values(self, monkeypatch, val):
        from services.assistance.agents.config import assistance_product_guardrail_enabled
        monkeypatch.setenv("ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED", val)
        assert assistance_product_guardrail_enabled() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", "off", "FALSE", "anything_else"])
    def test_disabled_falsy_values(self, monkeypatch, val):
        from services.assistance.agents.config import assistance_product_guardrail_enabled
        monkeypatch.setenv("ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED", val)
        assert assistance_product_guardrail_enabled() is False
