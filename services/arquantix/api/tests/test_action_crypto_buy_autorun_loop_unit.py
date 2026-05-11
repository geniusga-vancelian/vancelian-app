"""Tests d'intégration — court-circuits ``action`` CAL achat crypto."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.base import AgentEvent, AgentInput
from services.assistance.agents.runtime import agent_loop as agent_loop_module
from services.assistance.agents.runtime import run_agent_loop
from services.assistance.agents.tools.registry import tools_for
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    counter = {"n": 0}

    def _fake(*_a, **_kw):
        counter["n"] += 1
        return f"decision-{counter['n']}"

    monkeypatch.setattr(audit, "persist_decision", _fake)
    return counter


@pytest.fixture
def _fake_action_draft(monkeypatch):
    """Passe tous les chemins utilisant ``create_action_draft``."""

    def _create(_db, **_kwargs):
        row = MagicMock()
        row.id = uuid4()
        return row

    monkeypatch.setattr(
        "services.assistance.action_drafts_repo.create_action_draft",
        _create,
    )
    monkeypatch.setattr(
        "services.assistance.agents.tools.product.invest_confirmation_emit."
        "create_action_draft",
        _create,
    )


@pytest.fixture
def _noop_conversation_set_topic(monkeypatch):
    monkeypatch.setattr(
        agent_loop_module,
        "conversation_set_topic",
        MagicMock(),
    )


def _make_agent_input_amount_only_followup_btc() -> AgentInput:
    cid = str(uuid4())
    return AgentInput(
        user_message="1000€",
        recent_turns=[
            {
                "role": "assistant",
                "content": (
                    "Pour acheter du Bitcoin, pourrais-tu me confirmer "
                    "le montant que tu souhaites investir ?"
                ),
            },
            {"role": "user", "content": "1000€"},
        ],
        memory_state={
            "client_id": cid,
            "person_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
            "summarized_until_turn": None,
        },
    )


def _make_agent_input_post_confirm_compact() -> AgentInput:
    cid = str(uuid4())
    return AgentInput(
        user_message="",
        recent_turns=[
            {
                "role": "assistant",
                "content": "Récap précédent (QCM).",
            },
            {"role": "user", "content": ""},
        ],
        memory_state={
            "client_id": cid,
            "person_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
            "summarized_until_turn": None,
            "user_choice_hint": "crypto_buy_confirm_launch",
            "pending_action": {
                "target_kind": "crypto_buy",
                "target_id": "BTC",
                "amount_from": 1000.0,
                "currency_from": "EUR",
                "stage": "awaiting_launch_confirm",
            },
        },
    )


def _make_agent_input_first_turn_full_buy_btc() -> AgentInput:
    """Une seule entrée utilisateur avec intention + montant + actif (sans tour assistant prix)."""
    cid = str(uuid4())
    msg = "Je veux acheter 1000 euros de bitcoin"
    return AgentInput(
        user_message=msg,
        recent_turns=[{"role": "user", "content": msg}],
        memory_state={
            "client_id": cid,
            "person_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
            "summarized_until_turn": None,
        },
    )


def _make_agent_input_compound_memory_spurious_assistant_euro() -> AgentInput:
    """``compound_user_turn`` : bruit « 10 € » dans l’assistant, vrai montant dans le bloc user."""
    cid = str(uuid4())
    um = "Je veux acheter pour 1000 € de Bitcoin"
    compound = (
        "[RÉPONSE ASSISTANT PRÉCÉDENTE – référencée pour résoudre le tour courant]\n"
        "Certaines opérations peuvent coûter jusqu'à 10 € en frais.\n"
        "[DEMANDE / RÉPONSE UTILISATEUR SUR CE TOUR]\n"
        + um
    )
    return AgentInput(
        user_message=um,
        recent_turns=[
            {
                "role": "assistant",
                "content": "Certaines opérations peuvent coûter jusqu'à 10 € en frais.",
            },
            {"role": "user", "content": um},
        ],
        memory_state={
            "client_id": cid,
            "person_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
            "summarized_until_turn": None,
            "compound_user_turn": compound,
        },
    )

def _make_agent_input_no_buy_intent() -> AgentInput:
    cid = str(uuid4())
    return AgentInput(
        user_message="1000€",
        recent_turns=[
            {
                "role": "assistant",
                "content": "Le cours du Bitcoin varie fortement selon les marchés.",
            },
            {"role": "user", "content": "1000€"},
        ],
        memory_state={
            "client_id": cid,
            "person_id": str(uuid4()),
            "conversation_summary": None,
            "client_long_memory": None,
            "summarized_until_turn": None,
        },
    )


async def _collect_embeds_done(gen) -> tuple[list[AgentEvent], AgentEvent]:
    events: list[AgentEvent] = []
    done_ev: AgentEvent | None = None
    async for ev in gen:
        events.append(ev)
        if ev.type == "done":
            done_ev = ev
    assert done_ev is not None
    return events, done_ev


class TestActionCryptoBuyAutorunLoop:
    def test_autorun_mount_only_emits_launch_choices_then_skips_llm(
        self,
        _stub_persist_decision,
        _fake_action_draft,
        _noop_conversation_set_topic,
    ):
        calls = []

        def _completion(_messages, *, model, tools, tool_choice, temperature):
            calls.append(1)
            return {"content": "NE_DEVRAIT_PAS_ETRE_INVITE.", "tool_calls": None}

        ai = _make_agent_input_amount_only_followup_btc()
        conv_id = uuid4()

        events, done = asyncio.run(
            _collect_embeds_done(
                run_agent_loop(
                    agent_id="action",
                    system_prompt="# Agent action (test)",
                    available_tools=tools_for("action"),
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=conv_id,
                    user_id=1,
                    chat_completion_fn=_completion,
                )
            )
        )

        assert not calls, "Pas d’invocation LLM sur QCM préalable déterministe."
        choice_ev = next(e for e in events if e.type == "choices")
        assert "Récap" in (choice_ev.prompt or "")
        opt_ids = {o.id for o in (choice_ev.options or [])}
        assert "crypto_buy_confirm_launch" in opt_ids
        assert "crypto_buy_abort" in opt_ids
        assert done.embeds in (None, [])
        metrics = done.runtime_metrics or {}
        assert int(metrics.get("embeds_count", 0)) == 0

    def test_first_turn_full_buy_emits_launch_choices_then_skips_llm(
        self,
        _stub_persist_decision,
        _fake_action_draft,
        _noop_conversation_set_topic,
    ):
        """Bug historique : spec complète dès la 1ère phrase ne déclenchait pas la QCM."""
        calls = []

        def _completion(_messages, *, model, tools, tool_choice, temperature):
            calls.append(1)
            return {"content": "NE_DEVRAIT_PAS_ETRE_INVITE.", "tool_calls": None}

        ai = _make_agent_input_first_turn_full_buy_btc()
        conv_id = uuid4()

        events, done = asyncio.run(
            _collect_embeds_done(
                run_agent_loop(
                    agent_id="action",
                    system_prompt="# Agent action (test)",
                    available_tools=tools_for("action"),
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=conv_id,
                    user_id=1,
                    chat_completion_fn=_completion,
                )
            )
        )

        assert not calls
        choice_ev = next(e for e in events if e.type == "choices")
        assert "Récap" in (choice_ev.prompt or "")
        assert {o.id for o in (choice_ev.options or [])} >= {
            "crypto_buy_confirm_launch",
            "crypto_buy_abort",
        }
        assert done.embeds in (None, [])
        assert "1 000.00" in (choice_ev.prompt or "") or "1000" in (choice_ev.prompt or "")

    def test_compound_memory_ignores_assistant_euro_noise_for_launch_qcm(
        self,
        _stub_persist_decision,
        _fake_action_draft,
        _noop_conversation_set_topic,
    ):
        calls = []

        def _completion(_messages, *, model, tools, tool_choice, temperature):
            calls.append(1)
            return {"content": "NE_DEVRAIT_PAS_ETRE_INVITE.", "tool_calls": None}

        ai = _make_agent_input_compound_memory_spurious_assistant_euro()
        conv_id = uuid4()

        events, _done = asyncio.run(
            _collect_embeds_done(
                run_agent_loop(
                    agent_id="action",
                    system_prompt="# Agent action (test)",
                    available_tools=tools_for("action"),
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=conv_id,
                    user_id=1,
                    chat_completion_fn=_completion,
                )
            )
        )

        assert not calls
        choice_ev = next(e for e in events if e.type == "choices")
        prompt = choice_ev.prompt or ""
        assert "10.00" not in prompt and "10,00" not in prompt.replace(" ", "")
        assert "1 000" in prompt or "1000" in prompt
        assert "Bitcoin" in prompt

    def test_autorun_after_confirm_tap_injects_confirmation_embed(
        self,
        _stub_persist_decision,
        _fake_action_draft,
        _noop_conversation_set_topic,
    ):
        calls = []

        def _completion(_messages, *, model, tools, tool_choice, temperature):
            calls.append(1)
            return {
                "content": "tu peux valider depuis l'encart final.",
                "tool_calls": None,
            }

        ai = _make_agent_input_post_confirm_compact()
        conv_id = uuid4()

        events, done = asyncio.run(
            _collect_embeds_done(
                run_agent_loop(
                    agent_id="action",
                    system_prompt="# Agent action (test)",
                    available_tools=tools_for("action"),
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=conv_id,
                    user_id=1,
                    chat_completion_fn=_completion,
                )
            )
        )

        assert done.embeds
        emb = done.embeds[0]
        assert emb["type"] == "invest_confirmation_draft"
        assert emb.get("compact") is True
        assert calls, "Court texte après injection widget encore attendu."

    def test_no_autorun_when_assistant_missing_buy_verbs(
        self,
        _stub_persist_decision,
        _fake_action_draft,
        _noop_conversation_set_topic,
    ):
        def _completion(_messages, *, model, tools, tool_choice, temperature):
            return {"content": "Réponse sans widget.", "tool_calls": None}

        ai = _make_agent_input_no_buy_intent()
        conv_id = uuid4()

        _events, done = asyncio.run(
            _collect_embeds_done(
                run_agent_loop(
                    agent_id="action",
                    system_prompt="# Agent action (test)",
                    available_tools=tools_for("action"),
                    agent_input=ai,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=conv_id,
                    user_id=1,
                    chat_completion_fn=_completion,
                )
            )
        )

        assert not done.embeds
