"""Tests PR 4A — export golden traces structuralement."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from services.assistance.golden_trace_export import (
    build_trace_for_user_turn,
)


def _msg(
    *,
    turn_index: int,
    role: str,
    content: str = "",
    agent_used=None,
    message_type: str = "text",
    message_payload=None,
):
    return SimpleNamespace(
        turn_index=turn_index,
        role=role,
        content=content,
        agent_used=agent_used,
        message_type=message_type,
        message_payload=message_payload,
    )


def _dec(tool_name: str, **extra):
    return SimpleNamespace(
        id=uuid.uuid4(),
        agent_id="compliance",
        iteration=0,
        tool_name=tool_name,
        arguments_json={"k": "v"} if tool_name.startswith("policy") else {},
        result_summary={"status": "x"}
        if tool_name.startswith("policy")
        else None,
        correlation_id=None,
        created_at=None,
        **extra,
    )


def test_build_trace_policy_tools_and_embeddings():
    cid = uuid.uuid4()
    um = _msg(turn_index=4, role="user", content="Voir mon dépôt")

    rd = SimpleNamespace(
        id=uuid.uuid4(),
        arguments_json={
            "decision_kind": "route_to",
            "agent_id": "compliance",
            "confidence": 0.92,
            "orchestration": {"data_need": "transaction_data"},
            "conversation_state": {"ux": {"widget_pressure": "low"}},
        },
    )

    assistants = [
        _msg(
            turn_index=5,
            role="assistant",
            agent_used="compliance.transactional",
            content="Historique disponible.",
            message_payload={
                "embeds": [{"type": "transaction_detail", "transaction_id": "x"}],
            },
        ),
    ]

    interim = [_dec("list_transactions"), _dec("policy_data_need_reads")]

    trace = build_trace_for_user_turn(
        conversation_id=cid,
        user_message=um,
        assistants_for_turn=assistants,
        router_decision_row=rd,
        interim_decisions=interim,  # type: ignore[arg-type]
        recent_turn_messages=[um],
    )
    assert trace["conversation_id"] == str(cid)
    assert trace["tools_called"] == ["list_transactions"]
    assert len(trace["policy_gaps"]) == 1
    assert trace["policy_gaps"][0]["agent_id"] == "compliance"
    assert trace["final_message_type"] == "assistant_text_with_embeds"
    assert trace["embeds"][0]["type"] == "transaction_detail"
    assert trace["router_decision"]["agent_id"] == "compliance"
    assert trace["conversation_state"]["ux"]["widget_pressure"] == "low"
