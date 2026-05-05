"""Tests intégration SSE Lot 7 V1.1 — auto-QCM end-to-end.

Vérifie que :

  1. Quand un agent whitelisté streame une liste 3+ items + question,
     `stream_assistant_turn` :
       * yield un `done` qui contient ``auto_qcm`` ;
       * persiste un message texte avec ``message_payload.auto_qcm``.
  2. Quand le runtime émet déjà un `choices` via `ask_user_question`,
     l'auto-QCM ne s'ajoute pas (pas de double).
  3. Quand le tour porte un embed CTA built-in (``crypto_bundles_card``),
     l'auto-QCM ne s'émet pas.
  4. Quand `objective.stop_pushing` est True, l'auto-QCM ne s'émet pas.
  5. Quand `objective.next_best_action` ∈ {give_proof, …},
     l'auto-QCM ne s'émet pas.
  6. Le kill-switch ``ASSISTANCE_AUTO_QCM_ENABLED=false`` désactive tout.

Pas de DB réelle, pas de LLM réel : on monkey-patch `_run_via_runtime`
pour streamer une séquence d'``AgentEvent`` choisie + ``_persist_assistant_message``
pour capturer le payload persisté.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance import service as assistance_service
from services.assistance.agents.base import (
    AgentEvent,
    AgentInput,
    ChoiceOption,
    RouterDecision,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─── Helpers ──────────────────────────────────────────────────────────


_LISTING_TEXT_OK = (
    "Voici les options :\n"
    "1. Coffre Flexible\n"
    "2. Coffre Avenir\n"
    "3. Crypto Baskets\n"
    "Lequel t'intéresse ?"
)


def _make_router_decision(
    *,
    agent_id: str = "product",
    objective: Optional[dict] = None,
) -> RouterDecision:
    d = RouterDecision(
        agent_id=agent_id,
        confidence=0.9,
        reasoning="test",
    )
    if objective is not None:
        d.objective = objective
    return d


def _make_agent_input() -> AgentInput:
    return AgentInput(
        user_message="quelles offres ?",
        recent_turns=[],
        memory_state={
            "client_id": str(uuid4()),
            "person_id": str(uuid4()),
        },
    )


def _stream_factory(events: list[AgentEvent]):
    """Crée une fonction `event_iter`-style qui yield les events donnés."""

    async def _gen(*_args, **_kwargs):
        for ev in events:
            yield ev

    return _gen


def _events_text_only(text: str, *, embeds: Optional[list[dict]] = None) -> list[AgentEvent]:
    """Stream un seul delta + un done — pas de choices runtime."""
    return [
        AgentEvent(type="delta", content=text),
        AgentEvent(
            type="done",
            completed=True,
            embeds=list(embeds) if embeds else None,
        ),
    ]


def _events_with_runtime_choices(text: str) -> list[AgentEvent]:
    """Stream un delta + un choices (ask_user_question) + un done."""
    return [
        AgentEvent(type="delta", content=text),
        AgentEvent(
            type="choices",
            prompt="Quel projet veux-tu creuser ?",
            options=[
                ChoiceOption(id="opt_a", label="Maison"),
                ChoiceOption(id="opt_b", label="Retraite"),
            ],
            allow_freeform=True,
        ),
        AgentEvent(type="done", completed=True),
    ]


@pytest.fixture(autouse=True)
def _stub_runtime_persist(monkeypatch):
    """Stubs partagés à tous les tests de ce fichier :

      * `_persist_assistant_message` : retourne un MagicMock avec
        `.id = uuid4()`. Capture les kwargs reçus dans
        ``stub_state["last_persist_kwargs"]`` pour assertion.
      * `_schedule_consolidation` : no-op.
      * ``ASSISTANCE_RUNTIME_LOOP_ENABLED=true`` : chemine via Phase 2a
        et ``_run_via_runtime`` (mocké dans chaque test).
      * `assistance_service.session_factory` (passé en param) : non
        utilisé directement, on passe lambda: MagicMock.
    """
    monkeypatch.setenv("ASSISTANCE_RUNTIME_LOOP_ENABLED", "true")
    state: dict[str, Any] = {"last_persist_kwargs": None}

    def _fake_persist(*_args, **kwargs):
        state["last_persist_kwargs"] = dict(kwargs)
        m = MagicMock()
        m.id = uuid4()
        return m

    def _fake_consolidation(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        assistance_service,
        "_persist_assistant_message",
        _fake_persist,
    )
    monkeypatch.setattr(
        assistance_service,
        "_schedule_consolidation",
        _fake_consolidation,
    )
    return state


def _run_stream(events: list[AgentEvent], decision: RouterDecision) -> list[dict]:
    """Exécute `stream_assistant_turn` avec un runtime stubbé qui
    streame ``events``, et collecte les events SSE produits.
    """

    async def _do():
        async def _runtime_stub(*_args, **_kwargs):
            for ev in events:
                yield ev

        # Patch _run_via_runtime au moment de l'appel pour qu'il
        # retourne notre stub (qui est un async generator).
        original = assistance_service._run_via_runtime
        try:
            assistance_service._run_via_runtime = _runtime_stub
            out: list[dict] = []
            async for sse in assistance_service.stream_assistant_turn(
                session_factory=lambda: MagicMock(),
                conversation_id=uuid4(),
                user_idx=1,
                agent_input=_make_agent_input(),
                decision=decision,
                client_id=uuid4(),
                actor_kind=ActorKind.CUSTOMER,
                user_id=42,
                person_id=uuid4(),
            ):
                out.append(sse)
            return out
        finally:
            assistance_service._run_via_runtime = original

    return asyncio.run(_do())


# ─── 1. Cas nominal : auto-QCM émis ──────────────────────────────────


class TestAutoQcmNominal:
    def test_done_carries_auto_qcm(self, _stub_runtime_persist):
        events = _events_text_only(_LISTING_TEXT_OK)
        sse_events = _run_stream(
            events, _make_router_decision(agent_id="product")
        )
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" in done
        payload = done["auto_qcm"]
        assert payload["source"] == "auto_promoted"
        assert len(payload["options"]) == 3
        assert payload["options"][0]["label"] == "Coffre Flexible"
        assert payload["options"][0]["agent_hint"] == "product"

    def test_persisted_payload_contains_auto_qcm(self, _stub_runtime_persist):
        events = _events_text_only(_LISTING_TEXT_OK)
        _run_stream(events, _make_router_decision(agent_id="product"))
        kwargs = _stub_runtime_persist["last_persist_kwargs"]
        assert kwargs is not None
        payload = kwargs.get("message_payload")
        assert payload is not None
        assert "auto_qcm" in payload
        assert kwargs.get("message_type") == "text"  # pas modifié


# ─── 2. Pas de double-QCM si runtime a déjà émis choices ─────────────


class TestNoDoubleQcm:
    def test_runtime_choices_skips_auto_qcm(self, _stub_runtime_persist):
        events = _events_with_runtime_choices(_LISTING_TEXT_OK)
        sse_events = _run_stream(
            events, _make_router_decision(agent_id="product")
        )
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" not in done
        # Le message persisté est message_type=choices (le runtime_choices
        # pris la priorité), pas de auto_qcm dans le payload.
        kwargs = _stub_runtime_persist["last_persist_kwargs"]
        assert kwargs.get("message_type") == "choices"
        payload = kwargs.get("message_payload") or {}
        assert "auto_qcm" not in payload


# ─── 3. Embed CTA built-in court-circuite ────────────────────────────


class TestEmbedSkip:
    def test_crypto_bundles_card_skips(self, _stub_runtime_persist):
        events = _events_text_only(
            _LISTING_TEXT_OK,
            embeds=[{"type": "crypto_bundles_card", "data": {"items": []}}],
        )
        sse_events = _run_stream(
            events, _make_router_decision(agent_id="product")
        )
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" not in done
        # En revanche, embeds est bien propagé
        assert "embeds" in done

    def test_unknown_embed_does_not_skip(self, _stub_runtime_persist):
        events = _events_text_only(
            _LISTING_TEXT_OK,
            embeds=[{"type": "portfolio_allocation_donut", "data": {}}],
        )
        sse_events = _run_stream(
            events, _make_router_decision(agent_id="product")
        )
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" in done


# ─── 4. Objective stop_pushing court-circuite ────────────────────────


class TestObjectiveStopPushing:
    def test_stop_pushing_skips(self, _stub_runtime_persist):
        decision = _make_router_decision(
            agent_id="trust",
            objective={
                "primary_goal": "reassure",
                "next_best_action": "give_proof",
                "stop_pushing": True,
            },
        )
        events = _events_text_only(_LISTING_TEXT_OK)
        sse_events = _run_stream(events, decision)
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" not in done


# ─── 5. next_best_action interdit court-circuite ─────────────────────


class TestObjectiveForbiddenAction:
    @pytest.mark.parametrize(
        "nba", ["give_proof", "give_control", "micro_step", "call_to_action"]
    )
    def test_forbidden_action_skips(self, _stub_runtime_persist, nba):
        decision = _make_router_decision(
            agent_id="advisor",
            objective={
                "primary_goal": "inform",
                "next_best_action": nba,
                "stop_pushing": False,
            },
        )
        events = _events_text_only(_LISTING_TEXT_OK)
        sse_events = _run_stream(events, decision)
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" not in done

    @pytest.mark.parametrize(
        "nba", ["ask_question", "recommend"]
    )
    def test_allowed_action_promotes(self, _stub_runtime_persist, nba):
        decision = _make_router_decision(
            agent_id="advisor",
            objective={
                "primary_goal": "convert",
                "next_best_action": nba,
                "stop_pushing": False,
            },
        )
        events = _events_text_only(_LISTING_TEXT_OK)
        sse_events = _run_stream(events, decision)
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" in done


# ─── 6. Kill-switch env ──────────────────────────────────────────────


class TestKillSwitch:
    def test_env_disable_skips(self, _stub_runtime_persist, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_AUTO_QCM_ENABLED", "false")
        events = _events_text_only(_LISTING_TEXT_OK)
        sse_events = _run_stream(
            events, _make_router_decision(agent_id="product")
        )
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" not in done


# ─── 7. Listing trop court — pas de promote ──────────────────────────


class TestShortListing:
    def test_two_items_does_not_promote(self, _stub_runtime_persist):
        text_2 = (
            "Deux options :\n"
            "1. Plan A\n"
            "2. Plan B\n"
            "Lequel ?"
        )
        events = _events_text_only(text_2)
        sse_events = _run_stream(
            events, _make_router_decision(agent_id="product")
        )
        done = next(e for e in sse_events if e["type"] == "done")
        assert "auto_qcm" not in done
