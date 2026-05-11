"""Garde-fou « action_runtime_unavailable » — Phase 1 sécurité CAL.

Couvre :
  1. Intention transactionnelle + runtime Action indisponible (ex. loop off)
     → ``stream_assistant_turn`` n'appelle ni ``_run_via_runtime`` ni
     ``get_agent``. Message fixe + SSE ``done``.
  2. Intention transactionnelle + prérequis runtime OK → ``_run_via_runtime``
     est invoqué (stub).
  3. Question non transactionnelle → comportement nominal inchangé
     (toujours ``_run_via_runtime`` avec stub lorsque Phase 2a active).

Cf. ``services/assistance/action_runtime_guard.py``.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance import action_runtime_guard as arg
from services.assistance import service as assistance_service
from services.assistance.agents.base import (
    AGENT_ACTION_ID,
    AgentEvent,
    AgentInput,
    RouterDecision,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _txn_decision(*, agent_id: str = AGENT_ACTION_ID) -> RouterDecision:
    return RouterDecision(
        agent_id=agent_id,
        confidence=0.95,
        reasoning="buy btc",
        orchestration={
            "business_intent": "action_request",
            "transaction_kind": "crypto_buy",
        },
    )


def _product_decision() -> RouterDecision:
    return RouterDecision(
        agent_id="product",
        confidence=0.9,
        reasoning="wiki",
        orchestration={
            "business_intent": "product_education",
        },
    )


def _agent_input() -> AgentInput:
    return AgentInput(
        user_message="j'achète du BTC",
        recent_turns=[],
        memory_state={"client_id": str(uuid4())},
    )


@pytest.fixture(autouse=True)
def _stub_persist_and_consolid(monkeypatch):
    state: dict = {"persist_kwargs": None}

    def _fake_persist(*_args, **kwargs):
        state["persist_kwargs"] = kwargs
        m = MagicMock()
        m.id = uuid4()
        return m

    monkeypatch.setattr(
        assistance_service,
        "_persist_assistant_message",
        _fake_persist,
    )
    monkeypatch.setattr(
        assistance_service,
        "_schedule_consolidation",
        MagicMock(),
    )
    return state


def _collect_sse(monkeypatch, decision: RouterDecision) -> tuple[list[dict], list]:
    runtime_calls: list[bool] = []

    async def _runtime_stub(*_a, **_k):
        runtime_calls.append(True)
        yield AgentEvent(type="delta", content="stub runtime")
        yield AgentEvent(type="done", completed=True)

    monkeypatch.setattr(
        assistance_service,
        "_run_via_runtime",
        _runtime_stub,
    )

    async def _collect():
        out: list[dict] = []
        async for ev in assistance_service.stream_assistant_turn(
            session_factory=lambda: MagicMock(),
            conversation_id=uuid4(),
            user_idx=0,
            agent_input=_agent_input(),
            decision=decision,
            client_id=uuid4(),
            actor_kind=ActorKind.CUSTOMER,
            user_id=42,
            person_id=uuid4(),
        ):
            out.append(ev)
        return out

    sse = asyncio.run(_collect())
    return sse, runtime_calls


class TestTransactionalBlockedWhenLoopOff:
    def test_fallback_message_no_llm_path(self, _stub_persist_and_consolid, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_RUNTIME_LOOP_ENABLED", "false")
        gate_spy = MagicMock(wraps=arg.should_refuse_transactional_without_action_runtime)
        monkeypatch.setattr(
            arg,
            "should_refuse_transactional_without_action_runtime",
            gate_spy,
        )
        persisted: list[dict] = []

        def _persist_audit(*args, **kwargs):
            persisted.append(kwargs)

        monkeypatch.setattr(
            "services.assistance.agents.tools.shared.audit.persist_decision",
            _persist_audit,
        )

        spy_get_agent = MagicMock()
        monkeypatch.setattr(assistance_service, "get_agent", spy_get_agent)

        sse, runtime_calls = _collect_sse(monkeypatch, _txn_decision())

        assert gate_spy.called
        assert len(runtime_calls) == 0
        spy_get_agent.assert_not_called()

        deltas = [e for e in sse if e["type"] == "delta"]
        assert len(deltas) == 1
        assert arg.ACTION_RUNTIME_UNAVAILABLE_USER_FR in deltas[0]["content"]
        done = next(e for e in sse if e["type"] == "done")
        assert done["agent_used"] == AGENT_ACTION_ID
        assert done["message_type"] == "text"
        assert persisted, "persist_decision should be invoked"
        assert persisted[0].get("error_code") == "action_runtime_unavailable"
        assert persisted[0].get("tool_name") == "action_runtime_guard"
        args = persisted[0].get("arguments") or {}
        assert args.get("reason") == "action_runtime_unavailable"


class TestTransactionalUsesRuntimeWhenReady:
    def test_run_via_runtime_called(self, _stub_persist_and_consolid, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_RUNTIME_LOOP_ENABLED", "true")
        monkeypatch.delenv("ASSISTANCE_RUNTIME_LOOP_AGENTS", raising=False)
        spy_refuse = MagicMock(wraps=arg.should_refuse_transactional_without_action_runtime)
        monkeypatch.setattr(
            arg,
            "should_refuse_transactional_without_action_runtime",
            spy_refuse,
        )

        sse, runtime_calls = _collect_sse(monkeypatch, _txn_decision())

        assert spy_refuse.called
        assert len(runtime_calls) >= 1
        assert any(
            e.get("type") == "delta" and e.get("content") == "stub runtime"
            for e in sse
        )


class TestNonTransactionalUnchanged:
    def test_product_still_uses_runtime(self, _stub_persist_and_consolid, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_RUNTIME_LOOP_ENABLED", "true")
        monkeypatch.delenv("ASSISTANCE_RUNTIME_LOOP_AGENTS", raising=False)

        sse, runtime_calls = _collect_sse(monkeypatch, _product_decision())

        assert len(runtime_calls) >= 1
        assert any(
            e.get("type") == "delta" and e.get("content") == "stub runtime"
            for e in sse
        )
