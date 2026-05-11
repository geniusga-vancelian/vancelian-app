"""Tests deux étapes ``crypto_buy_start`` : QCM « lancer » puis widget définitif."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.tools.action import crypto_buy_start
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared.classify_actor import ActorKind


@pytest.fixture
def patched_drafts(monkeypatch):
    def _mk(_db, **_kwargs):
        row = MagicMock()
        row.id = uuid4()
        return row

    monkeypatch.setattr(
        "services.assistance.action_drafts_repo.create_action_draft",
        _mk,
    )
    monkeypatch.setattr(
        "services.assistance.agents.tools.product.invest_confirmation_emit."
        "create_action_draft",
        _mk,
    )


def _ctx(**kw) -> ToolContext:
    base = dict(
        db=MagicMock(),
        client_id=str(uuid4()),
        person_id=None,
        user_id=1,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="action",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="x",
    )
    base.update(kw)
    return ToolContext(**base)


def test_first_pass_emits_launch_interrupt(patched_drafts):
    ctx = _ctx()
    res = crypto_buy_start.execute(
        ctx,
        symbol="BTC",
        amount_from=1000.0,
        currency_from="EUR",
    )
    assert res.get("ok") is True
    assert res.get("interrupt_with_question") is True
    assert res.get("mode") == "awaiting_launch_confirm"
    assert res.get("allow_freeform") is False
    oids = {o["id"] for o in (res.get("options") or [])}
    assert "crypto_buy_confirm_launch" in oids
    assert "crypto_buy_abort" in oids


def test_second_pass_confirm_hint_emits_invest_confirmation(patched_drafts):
    pend = {
        "target_kind": "crypto_buy",
        "target_id": "BTC",
        "amount_from": 1000.0,
        "currency_from": "EUR",
        "stage": "awaiting_launch_confirm",
    }
    ctx = _ctx(
        pending_action_snapshot=pend,
        user_choice_hint="crypto_buy_confirm_launch",
        intake_user_text="",
    )
    res = crypto_buy_start.execute(
        ctx,
        symbol="BTC",
        amount_from=1000.0,
        currency_from="EUR",
    )
    assert res.get("ok") is True
    assert res.get("mode") == "investment_confirmation_compact"
    emb = ctx.embeds_to_emit[-1]
    assert emb["type"] == "invest_confirmation_draft"
