"""Tests émission embed ``invest_confirmation_draft`` (module partagé)."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.product.invest_confirmation_emit import (
    append_invest_confirmation_embed,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


@pytest.fixture
def tool_ctx() -> ToolContext:
    db = MagicMock()
    return ToolContext(
        db=db,
        client_id=str(uuid4()),
        person_id=None,
        user_id=1,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="action",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="c1",
    )


def test_append_sets_compact_and_intent_kind(tool_ctx: ToolContext, monkeypatch):
    created: dict = {}

    def _fake_create(db, **kwargs):
        row = MagicMock()
        row.id = uuid4()
        created["payload"] = kwargs.get("payload")
        return row

    monkeypatch.setattr(
        "services.assistance.agents.tools.product.invest_confirmation_emit.create_action_draft",
        _fake_create,
    )

    res = append_invest_confirmation_embed(
        tool_ctx,
        target_kind="crypto_buy",
        target_id="BTC",
        amount=1000.0,
        amount_currency="EUR",
        account_key="fiat",
        source_label="Compte Euro",
        destination_label="Achat · Bitcoin (BTC)",
        intent_kind="crypto_buy",
        compact=True,
    )
    assert res["ok"] is True
    assert created["payload"]["compact"] is True
    assert created["payload"]["intent_kind"] == "crypto_buy"
    emb = tool_ctx.embeds_to_emit[-1]
    assert emb["type"] == "invest_confirmation_draft"
    assert emb["compact"] is True
    assert emb["presentation"] == "compact_card"
    assert emb["intent_kind"] == "crypto_buy"
    assert "confirm_deep_link" in emb

