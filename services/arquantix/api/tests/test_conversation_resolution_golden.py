"""Phase 5 — scénarios dorés ``conversation_resolution`` (heuristique + apply)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.action_lifecycle import MESSAGE_ACTION_DRAFT_EXPIRED_FR
from services.assistance.conversation_resolution import (
    ResolutionMetrics,
    apply_conversation_resolution,
    build_resolution_result,
    heuristic_resolution_development_only,
    resolution_from_classifier_signal,
)


@pytest.fixture(autouse=True)
def _reset_resolution_metrics():
    ResolutionMetrics.reset()
    yield
    ResolutionMetrics.reset()


def _pend_btc() -> dict:
    return {
        "action_draft_id": str(uuid4()),
        "action_type": "crypto_buy",
        "status": "draft",
        "target_id": "BTC",
        "stage": "awaiting_launch_confirm",
    }


def test_golden_case1_continuation_oui() -> None:
    r = heuristic_resolution_development_only("oui", _pend_btc())
    assert r.resolution_type == "same_action_continuation"
    assert r.should_keep_active_draft


def test_golden_case1_amount_euros() -> None:
    r = heuristic_resolution_development_only("1000 euros", _pend_btc())
    assert r.resolution_type == "same_action_continuation"


def test_golden_case2_new_subject_finally_eth() -> None:
    r = heuristic_resolution_development_only(
        "finalement achète de l'ETH", _pend_btc()
    )
    assert r.resolution_type == "new_action_detected"
    assert r.should_supersede_active_draft


def test_golden_case2_eth_while_btc_pending() -> None:
    r = heuristic_resolution_development_only("ETH stp", _pend_btc())
    assert r.resolution_type == "new_action_detected"


def test_golden_case3_cancel() -> None:
    r = heuristic_resolution_development_only("laisse tomber", _pend_btc())
    assert r.resolution_type == "cancel_requested"
    assert r.should_cancel_active_draft


def test_golden_case4_off_topic_vault_yield() -> None:
    r = heuristic_resolution_development_only(
        "c'est quoi le rendement du coffre ?", _pend_btc()
    )
    assert r.resolution_type == "off_topic"
    assert r.should_keep_active_draft


def test_golden_case5_stale_continuation_after_expiry() -> None:
    db = MagicMock()
    conv = uuid4()
    res = build_resolution_result(
        "same_action_continuation",
        reason="user_confirms_after_ttl",
    )
    out = apply_conversation_resolution(
        db,
        conversation_id=conv,
        resolution=res,
        trigger_source="user",
        stale_continuation_without_draft=True,
    )
    assert out.lifecycle_decision == "restart_flow_suggested"
    assert out.user_guidance_hint_fr == MESSAGE_ACTION_DRAFT_EXPIRED_FR
    snap = ResolutionMetrics.snapshot()
    assert snap.get("restart_after_expiry", 0) >= 1


def test_apply_supersede_calls_repo() -> None:
    db = MagicMock()
    conv = uuid4()
    res = build_resolution_result("new_action_detected", target_action_type="crypto_buy")
    with patch(
        "services.assistance.conversation_resolution.supersede_previous_drafts",
        return_value=1,
    ) as sup:
        out = apply_conversation_resolution(
            db,
            conversation_id=conv,
            resolution=res,
            active_action_snapshot=_pend_btc(),
        )
        sup.assert_called_once_with(
            db,
            conversation_id=conv,
            trigger_source="llm_classifier",
        )
    assert out.lifecycle_decision == "superseded"
    assert out.superseded_count == 1
    assert ResolutionMetrics.snapshot().get("supersede", 0) >= 1


def test_apply_cancel_calls_repo() -> None:
    db = MagicMock()
    conv = uuid4()
    res = build_resolution_result("cancel_requested")
    with patch(
        "services.assistance.conversation_resolution.cancel_active_action_drafts",
        return_value=1,
    ) as canc:
        out = apply_conversation_resolution(
            db,
            conversation_id=conv,
            resolution=res,
            active_action_snapshot=_pend_btc(),
        )
        canc.assert_called_once_with(
            db,
            conversation_id=conv,
            trigger_source="user",
        )
    assert out.lifecycle_decision == "cancelled"


def test_classifier_mapping_round_trip() -> None:
    full, local = resolution_from_classifier_signal(
        "ambiguous",
        confidence=0.4,
        reason="llm",
    )
    assert local == "clarification"
    assert full.resolution_type == "ambiguous"
