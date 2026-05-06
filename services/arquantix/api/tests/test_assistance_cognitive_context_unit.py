"""Tests unitaires Cognitive Bot v4 — Lot 2 « Cognitive State injecté
dans chaque sub-agent » (2026-05-06).

Couvre :

  * Helpers ``tools/shared/cognitive_context.py`` (lecture défensive
    de ``ctx.cognitive_state`` et ``ctx.objective``).
  * ``ToolContext`` accepte les nouveaux champs optionnels et les
    expose immutables (``frozen=True``).
  * Plumbing ``agent_loop.run_agent_loop`` : les snapshots posés
    dans ``memory_state`` sont recopiés dans ``ToolContext`` avant
    appel ``_execute_tool``.
  * Propagation cross-agent : ``_run_consult_specialist`` transmet
    ``cognitive_state`` + ``objective`` au sub-runtime (fix bug
    latent où le specialist consulté voyait un état neutre).
  * Cohérence des constantes (``URGENT_EMOTIONS`` ⊂
    ``KNOWN_EMOTIONAL_INTENTS``).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.base import AgentInput
from services.assistance.agents.cognitive_state import (
    KNOWN_EMOTIONAL_INTENTS,
    KNOWN_KNOWLEDGE_LEVELS,
    KNOWN_STAGES,
)
from services.assistance.agents.conversation_objective import (
    KNOWN_ACTIONS,
    KNOWN_GOALS,
)
from services.assistance.agents.runtime import run_agent_loop
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.assistance.agents.tools.shared.cognitive_context import (
    URGENT_EMOTIONS,
    cognitive_snapshot,
    get_conversation_stage,
    get_emotional_intent,
    get_knowledge_level,
    get_next_best_action,
    get_primary_goal,
    get_strategy_hint,
    get_trust_level,
    should_stop_pushing,
)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _make_ctx(
    *,
    cognitive_state: dict | None = None,
    objective: dict | None = None,
    agent_id: str = "compliance.transactional",
) -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=str(uuid4()),
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id=agent_id,
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-cog-l2",
        cognitive_state=cognitive_state,
        objective=objective,
    )


# ─────────────────────────────────────────────────────────────────────
# A. ToolContext — accepte les nouveaux champs et reste immutable
# ─────────────────────────────────────────────────────────────────────


class TestToolContextCognitiveFields:
    def test_default_to_none(self):
        ctx = ToolContext(
            db=MagicMock(),
            client_id=None,
            person_id=None,
            user_id=1,
            actor_kind=ActorKind.CUSTOMER,
            agent_id="product",
            conversation_id="c",
            iteration=0,
            audit_session_id="s",
            correlation_id="r",
        )
        assert ctx.cognitive_state is None
        assert ctx.objective is None

    def test_accepts_dict_payloads(self):
        ctx = _make_ctx(
            cognitive_state={
                "emotional_intent": "fear",
                "trust_level": 0.42,
            },
            objective={"primary_goal": "reassure", "stop_pushing": True},
        )
        assert ctx.cognitive_state["emotional_intent"] == "fear"
        assert ctx.objective["stop_pushing"] is True

    def test_frozen_prevents_reassignment(self):
        ctx = _make_ctx(cognitive_state={"emotional_intent": "neutral"})
        with pytest.raises(FrozenInstanceError):
            ctx.cognitive_state = {"emotional_intent": "anger"}  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────
# B. Helpers cognitive_context — fallbacks défensifs
# ─────────────────────────────────────────────────────────────────────


class TestHelpersFallbacks:
    def test_all_helpers_default_when_state_missing(self):
        ctx = _make_ctx()
        assert get_emotional_intent(ctx) == "neutral"
        assert get_conversation_stage(ctx) == "discovery"
        assert get_trust_level(ctx) == 0.5
        assert get_knowledge_level(ctx) == "low"
        assert get_primary_goal(ctx) == "inform"
        assert get_next_best_action(ctx) == "ask_question"
        assert should_stop_pushing(ctx) is False
        assert get_strategy_hint(ctx) is None

    @pytest.mark.parametrize(
        "bad_value",
        [None, "not-a-dict", 42, [], object()],
    )
    def test_helpers_robust_against_garbage_state(self, bad_value):
        ctx = _make_ctx(cognitive_state=bad_value, objective=bad_value)
        assert get_emotional_intent(ctx) == "neutral"
        assert get_trust_level(ctx) == 0.5
        assert should_stop_pushing(ctx) is False

    def test_unknown_emotion_falls_back_to_neutral(self):
        ctx = _make_ctx(cognitive_state={"emotional_intent": "ZZZ"})
        assert get_emotional_intent(ctx) == "neutral"

    def test_unknown_stage_falls_back_to_discovery(self):
        ctx = _make_ctx(cognitive_state={"conversation_stage": "ZZZ"})
        assert get_conversation_stage(ctx) == "discovery"

    def test_unknown_goal_falls_back_to_inform(self):
        ctx = _make_ctx(objective={"primary_goal": "ZZZ"})
        assert get_primary_goal(ctx) == "inform"

    def test_unknown_action_falls_back_to_ask_question(self):
        ctx = _make_ctx(objective={"next_best_action": "ZZZ"})
        assert get_next_best_action(ctx) == "ask_question"

    def test_trust_level_clamped_above_one(self):
        ctx = _make_ctx(cognitive_state={"trust_level": 5.0})
        assert get_trust_level(ctx) == 1.0

    def test_trust_level_clamped_below_zero(self):
        ctx = _make_ctx(cognitive_state={"trust_level": -1.5})
        assert get_trust_level(ctx) == 0.0

    def test_trust_level_string_parsed(self):
        ctx = _make_ctx(cognitive_state={"trust_level": "0.73"})
        assert get_trust_level(ctx) == pytest.approx(0.73)

    def test_trust_level_garbage_falls_back(self):
        ctx = _make_ctx(cognitive_state={"trust_level": "boom"})
        assert get_trust_level(ctx) == 0.5

    def test_strategy_hint_truncated_to_300(self):
        long = "x" * 500
        ctx = _make_ctx(objective={"strategy_hint": long})
        out = get_strategy_hint(ctx)
        assert out is not None
        assert len(out) == 300


# ─────────────────────────────────────────────────────────────────────
# C. should_stop_pushing — règles métier
# ─────────────────────────────────────────────────────────────────────


class TestShouldStopPushing:
    def test_explicit_objective_wins(self):
        """Si ``objective.stop_pushing`` est explicite, il prime sur
        l'inférence depuis ``emotional_intent``."""
        # Cas paradoxal mais légitime : NEUTRAL + objectif Reassurance
        # forcé par un override aval (ex. patch produit).
        ctx = _make_ctx(
            cognitive_state={"emotional_intent": "neutral"},
            objective={"stop_pushing": True},
        )
        assert should_stop_pushing(ctx) is True

    def test_explicit_objective_false_overrides_emotion(self):
        ctx = _make_ctx(
            cognitive_state={"emotional_intent": "fear"},
            objective={"stop_pushing": False},
        )
        assert should_stop_pushing(ctx) is False

    @pytest.mark.parametrize("emotion", sorted(URGENT_EMOTIONS))
    def test_urgent_emotion_triggers_stop_when_no_explicit_objective(
        self, emotion
    ):
        ctx = _make_ctx(cognitive_state={"emotional_intent": emotion})
        assert should_stop_pushing(ctx) is True

    @pytest.mark.parametrize(
        "emotion", ["neutral", "curiosity", "transaction", "opportunity"]
    )
    def test_non_urgent_emotion_does_not_stop_by_default(self, emotion):
        ctx = _make_ctx(cognitive_state={"emotional_intent": emotion})
        assert should_stop_pushing(ctx) is False


# ─────────────────────────────────────────────────────────────────────
# D. cognitive_snapshot — sortie stable
# ─────────────────────────────────────────────────────────────────────


class TestCognitiveSnapshot:
    def test_snapshot_keys_complete(self):
        ctx = _make_ctx()
        snap = cognitive_snapshot(ctx)
        assert set(snap.keys()) == {
            "emotional_intent",
            "conversation_stage",
            "trust_level",
            "knowledge_level",
            "primary_goal",
            "next_best_action",
            "stop_pushing",
        }

    def test_snapshot_serializable(self):
        ctx = _make_ctx(
            cognitive_state={
                "emotional_intent": "fear",
                "trust_level": 0.31,
            },
            objective={"primary_goal": "reassure", "stop_pushing": True},
        )
        # Doit être JSON-serializable sans encoder custom.
        s = json.dumps(cognitive_snapshot(ctx))
        round_trip = json.loads(s)
        assert round_trip["emotional_intent"] == "fear"
        assert round_trip["primary_goal"] == "reassure"
        assert round_trip["stop_pushing"] is True


# ─────────────────────────────────────────────────────────────────────
# E. Cohérence avec les modules amont
# ─────────────────────────────────────────────────────────────────────


class TestConstantsAlignedWithAmont:
    def test_urgent_emotions_subset_of_known(self):
        assert URGENT_EMOTIONS.issubset(KNOWN_EMOTIONAL_INTENTS)

    def test_helper_known_emotions_match_amont(self):
        from services.assistance.agents.tools.shared import (
            cognitive_context as cc,
        )
        assert cc._KNOWN_EMOTIONS == frozenset(KNOWN_EMOTIONAL_INTENTS)

    def test_helper_known_stages_match_amont(self):
        from services.assistance.agents.tools.shared import (
            cognitive_context as cc,
        )
        assert cc._KNOWN_STAGES == frozenset(KNOWN_STAGES)

    def test_helper_known_goals_match_amont(self):
        from services.assistance.agents.tools.shared import (
            cognitive_context as cc,
        )
        assert cc._KNOWN_GOALS == frozenset(KNOWN_GOALS)

    def test_helper_known_actions_match_amont(self):
        from services.assistance.agents.tools.shared import (
            cognitive_context as cc,
        )
        assert cc._KNOWN_ACTIONS == frozenset(KNOWN_ACTIONS)

    def test_knowledge_levels_match_amont(self):
        # Sanity check du fallback côté helper.
        for lvl in ("low", "medium", "high"):
            assert lvl in KNOWN_KNOWLEDGE_LEVELS


# ─────────────────────────────────────────────────────────────────────
# F. Plumbing run_agent_loop — ToolContext peuplé depuis memory_state
# ─────────────────────────────────────────────────────────────────────


def _make_completion_fn(responses: list[dict]):
    state = {"i": 0}

    def _fn(messages, *, model, tools, tool_choice, temperature):
        i = state["i"]
        state["i"] += 1
        if i >= len(responses):
            return {"content": "FALLBACK_END", "tool_calls": None}
        return responses[i]

    return _fn


def _capture_ctx_tool(captured_refs: list[ToolContext]):
    """Tool factice qui capture le ``ToolContext`` reçu pour assertion."""
    spec: ToolSpec = {
        "type": "function",
        "function": {
            "name": "capture_ctx_tool",
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

    def execute(ctx, **kwargs):
        captured_refs.append(ctx)
        return {"ok": True}

    return type(
        "Mod", (), {"SPEC": spec, "execute": staticmethod(execute)}
    )


def _tool_call(name: str, *, call_id: str = "c0"):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": "{}"},
    }


async def _collect(gen):
    return [ev async for ev in gen]


@pytest.fixture(autouse=True)
def _stub_persist_decision(monkeypatch):
    def _fake(*args, **kwargs):
        return f"decision-{uuid4()}"

    monkeypatch.setattr(audit, "persist_decision", _fake)


class TestRuntimePlumbing:
    def test_ctx_receives_cognitive_state_and_objective(self):
        captured: list[ToolContext] = []
        tool = _capture_ctx_tool(captured)
        completion = _make_completion_fn([
            {
                "content": None,
                "tool_calls": [_tool_call("capture_ctx_tool", call_id="c1")],
            },
            {"content": "Done.", "tool_calls": None},
        ])

        agent_input = AgentInput(
            user_message="je suis inquiet",
            recent_turns=[],
            memory_state={
                "client_id": str(uuid4()),
                "cognitive_state": {
                    "emotional_intent": "fear",
                    "conversation_stage": "discovery",
                    "trust_level": 0.30,
                    "knowledge_level": "low",
                },
                "objective": {
                    "primary_goal": "reassure",
                    "next_best_action": "give_proof",
                    "stop_pushing": True,
                    "strategy_hint": "Désamorcer la peur d'abord.",
                },
            },
        )

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=agent_input,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        assert len(captured) == 1
        ctx = captured[0]
        # ── Lecture brute via dataclass.
        assert ctx.cognitive_state == agent_input.memory_state["cognitive_state"]
        assert ctx.objective == agent_input.memory_state["objective"]
        # ── Lecture via helpers.
        assert get_emotional_intent(ctx) == "fear"
        assert get_trust_level(ctx) == pytest.approx(0.30)
        assert should_stop_pushing(ctx) is True
        assert get_strategy_hint(ctx) == "Désamorcer la peur d'abord."

    def test_ctx_handles_missing_cognitive_state_gracefully(self):
        captured: list[ToolContext] = []
        tool = _capture_ctx_tool(captured)
        completion = _make_completion_fn([
            {
                "content": None,
                "tool_calls": [_tool_call("capture_ctx_tool")],
            },
            {"content": "Done.", "tool_calls": None},
        ])

        agent_input = AgentInput(
            user_message="hello",
            recent_turns=[],
            memory_state={"client_id": str(uuid4())},
        )

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=agent_input,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        assert len(captured) == 1
        ctx = captured[0]
        assert ctx.cognitive_state is None
        assert ctx.objective is None
        # Helpers tournent sans crasher.
        assert get_emotional_intent(ctx) == "neutral"
        assert should_stop_pushing(ctx) is False

    def test_ctx_rejects_garbage_cognitive_state(self):
        """Si memory_state contient une valeur non-dict (legacy / bug),
        le runtime doit la **remplacer par None** pour ne pas casser
        les helpers qui attendent un dict."""
        captured: list[ToolContext] = []
        tool = _capture_ctx_tool(captured)
        completion = _make_completion_fn([
            {
                "content": None,
                "tool_calls": [_tool_call("capture_ctx_tool")],
            },
            {"content": "Done.", "tool_calls": None},
        ])

        agent_input = AgentInput(
            user_message="hello",
            recent_turns=[],
            memory_state={
                "client_id": str(uuid4()),
                "cognitive_state": "not-a-dict-oops",
                "objective": 42,
            },
        )

        asyncio.run(
            _collect(
                run_agent_loop(
                    agent_id="product",
                    system_prompt="prompt",
                    available_tools=[tool],
                    agent_input=agent_input,
                    actor_kind=ActorKind.CUSTOMER,
                    db=MagicMock(),
                    conversation_id=uuid4(),
                    user_id=42,
                    chat_completion_fn=completion,
                )
            )
        )

        assert len(captured) == 1
        ctx = captured[0]
        assert ctx.cognitive_state is None
        assert ctx.objective is None


# ─────────────────────────────────────────────────────────────────────
# G. Propagation cross-agent — _run_consult_specialist
# ─────────────────────────────────────────────────────────────────────


class TestConsultSpecialistPropagation:
    """Lot 2 fix : ``_run_consult_specialist`` doit transmettre
    ``cognitive_state`` + ``objective`` au sub-runtime, sinon le
    specialist consulté voit un état neutre par défaut et peut
    enchaîner sur de la recommandation alors que le caller est en
    ``stop_pushing=True``."""

    def test_sub_runtime_receives_caller_cognitive_state(self, monkeypatch):
        from services.assistance.agents.runtime import agent_loop as al_module

        captured_inputs: list[AgentInput] = []

        async def fake_run_agent_loop(**kwargs):
            captured_inputs.append(kwargs.get("agent_input"))
            # Yield un seul delta pour que la consultation soit
            # considérée comme réussie côté caller.
            from services.assistance.agents.base import AgentEvent

            yield AgentEvent(type="delta", content="proxy answer")

        monkeypatch.setattr(
            al_module, "run_agent_loop", fake_run_agent_loop
        )

        caller_input = AgentInput(
            user_message="je suis inquiet pour mon argent",
            recent_turns=[],
            memory_state={
                "client_id": "client-123",
                "person_id": "person-456",
                "cognitive_state": {
                    "emotional_intent": "fear",
                    "trust_level": 0.25,
                },
                "objective": {
                    "primary_goal": "reassure",
                    "stop_pushing": True,
                    "strategy_hint": "rassurer d'abord",
                },
            },
        )

        text, duration_ms = asyncio.run(
            al_module._run_consult_specialist(
                target_agent="product",
                question="les frais Vault",
                agent_input=caller_input,
                actor_kind=ActorKind.CUSTOMER,
                db=MagicMock(),
                conversation_id=uuid4(),
                user_id=42,
                correlation_id="t-corr",
                chat_completion_fn=lambda *a, **k: None,
                chain_depth=0,
            )
        )

        assert text == "proxy answer"
        assert duration_ms >= 0
        assert len(captured_inputs) == 1
        sub_input = captured_inputs[0]
        # Identité préservée.
        assert sub_input.memory_state["client_id"] == "client-123"
        assert sub_input.memory_state["person_id"] == "person-456"
        # ── Cœur du test : Cognitive Bot v4 propagé.
        assert sub_input.memory_state["cognitive_state"] == (
            caller_input.memory_state["cognitive_state"]
        )
        assert sub_input.memory_state["objective"] == (
            caller_input.memory_state["objective"]
        )

    def test_sub_runtime_propagates_none_when_caller_has_no_state(
        self, monkeypatch
    ):
        from services.assistance.agents.runtime import agent_loop as al_module

        captured_inputs: list[AgentInput] = []

        async def fake_run_agent_loop(**kwargs):
            captured_inputs.append(kwargs.get("agent_input"))
            from services.assistance.agents.base import AgentEvent

            yield AgentEvent(type="delta", content="ok")

        monkeypatch.setattr(
            al_module, "run_agent_loop", fake_run_agent_loop
        )

        caller_input = AgentInput(
            user_message="x",
            recent_turns=[],
            memory_state={"client_id": "cid"},
        )

        asyncio.run(
            al_module._run_consult_specialist(
                target_agent="product",
                question="x",
                agent_input=caller_input,
                actor_kind=ActorKind.CUSTOMER,
                db=MagicMock(),
                conversation_id=uuid4(),
                user_id=1,
                correlation_id="t",
                chat_completion_fn=lambda *a, **k: None,
                chain_depth=0,
            )
        )

        sub_input = captured_inputs[0]
        # Les clés sont présentes mais à None — c'est important pour
        # que le runtime distingue « rien à propager » (None) d'une
        # absence non intentionnelle.
        assert "cognitive_state" in sub_input.memory_state
        assert sub_input.memory_state["cognitive_state"] is None
        assert "objective" in sub_input.memory_state
        assert sub_input.memory_state["objective"] is None
