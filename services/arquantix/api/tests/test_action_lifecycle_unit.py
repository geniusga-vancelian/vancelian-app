"""Phase 4 — machine d'état ``AssistanceActionDraft`` (``action_lifecycle``)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


from services.assistance.action_lifecycle import (
    InvalidLifecycleTransition,
    apply_transition_to_sql_row,
    assert_can_transition,
    can_transition_lifecycle,
    classify_interruption_resolution,
    effective_lifecycle_state,
    ensure_payload_mutable_for_confirmed,
    is_action_draft_expired,
    merge_lifecycle_block,
    persist_lifecycle_transition_audit_with_log,
    seed_initial_lifecycle,
)


def test_allowed_and_forbidden_transition_table() -> None:
    assert can_transition_lifecycle("collecting", "awaiting_confirmation")
    assert_can_transition(
        "awaiting_confirmation",
        "confirmed",
    )
    assert not can_transition_lifecycle("confirmed", "collecting")
    assert not can_transition_lifecycle("expired", "confirmed")
    assert not can_transition_lifecycle("cancelled", "confirmed")
    assert not can_transition_lifecycle("superseded", "confirmed")
    with pytest.raises(InvalidLifecycleTransition):
        assert_can_transition("confirmed", "awaiting_confirmation")


def test_ttl_expired_detection() -> None:
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    pl_true = {"cal_contract": {"expires_at": past}}
    assert is_action_draft_expired(payload=pl_true)
    fut = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    assert not is_action_draft_expired(payload={"cal_contract": {"expires_at": fut}})
    assert not is_action_draft_expired(payload={})


def test_effective_state_macro_vs_payload() -> None:
    ls = effective_lifecycle_state(
        column_status="draft",
        payload={"stage": "source_list"},
    )
    assert ls == "collecting"


def test_classify_interruption_backend_only() -> None:
    assert classify_interruption_resolution("same_action_continuation") == "noop"
    assert classify_interruption_resolution("new_action_detected") == "supersede"
    assert classify_interruption_resolution("cancel_requested") == "cancel"
    assert classify_interruption_resolution("off_topic") == "preserve_active_draft"
    assert classify_interruption_resolution("ambiguous") == "clarification"
    assert classify_interruption_resolution("no_active_action") == "noop"


def test_immuable_confirmed_merge_guard() -> None:
    payload = {"_lifecycle": {"state": "confirmed"}}
    with pytest.raises(ValueError, match="action_draft_confirmed_immutable"):
        ensure_payload_mutable_for_confirmed(payload)


def test_merge_lifecycle_preserves_execution_placeholders() -> None:
    pl: dict = {"_lifecycle": {"execution_reference": "x", "execution_status": "pending"}}
    merge_lifecycle_block(
        pl,
        state="awaiting_confirmation",
        reason="invalidated",
        trigger="system",
    )
    assert pl["_lifecycle"]["execution_reference"] == "x"


def test_apply_transition_row_and_audit_mock() -> None:
    row = MagicMock()
    row.id = uuid4()
    row.conversation_id = uuid4()
    row.action_type = "crypto_buy"
    row.status = "draft"
    row.payload = {
        "stage": "confirmation",
        "cal_contract": {
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat().replace("+00:00", "Z"),
        },
    }

    evt = apply_transition_to_sql_row(
        row,
        to_lifecycle="confirmed",
        reason="confirmed_by_user",
        trigger="user",
        execution_reference="ref-1",
        execution_status="submitted",
    )
    assert evt.previous_state == "awaiting_confirmation"
    assert evt.new_state == "confirmed"
    assert row.status == "confirmed"

    with patch(
        "services.assistance.action_lifecycle.persist_lifecycle_transition_audit"
    ) as p_audit:
        p_audit.return_value = "audit-1"
        out = persist_lifecycle_transition_audit_with_log(
            MagicMock(),
            evt=evt,
        )
        assert out == "audit-1"
        p_audit.assert_called_once()


def test_seed_initial_lifecycle_injects_block() -> None:
    pl: dict = {
        "stage": "source_list",
        "target_kind": "crypto_buy",
        "target_id": "ETH",
        "accounts_count": 2,
        "cal_contract": {"expires_at": "2099-01-01T00:00:00+00:00"},
    }
    seed_initial_lifecycle(pl, action_type="crypto_buy", trigger="runtime_tool")
    assert pl["_lifecycle"]["state"] == "collecting"
    assert pl["_lifecycle"]["trigger_source"] == "runtime_tool"


def test_transition_superseded_from_collecting() -> None:
    row = MagicMock()
    row.id = uuid4()
    row.conversation_id = uuid4()
    row.action_type = "crypto_buy"
    row.status = "draft"
    row.payload = {
        "stage": "source_list",
        "accounts_count": 1,
        "target_kind": "crypto_buy",
        "target_id": "BTC",
        "_lifecycle": {"state": "collecting"},
    }
    evt = apply_transition_to_sql_row(
        row,
        to_lifecycle="superseded",
        reason="superseded_by_new_action",
        trigger="runtime_tool",
    )
    assert evt.previous_state == "collecting"
    assert row.status == "superseded"
