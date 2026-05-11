"""Phase 6 — schéma strict + pont LLM (validation, adapter, métriques)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.conversation_resolution_llm import (
    StructuredResolutionMetrics,
    build_resolution_result_from_llm_signal,
    maybe_apply_llm_resolution,
)
from services.assistance.llm_resolution_schema import (
    LLMConversationResolutionSignal,
    parse_llm_resolution_json_any,
    parse_llm_resolution_json_string,
    strip_llm_json_fences,
)


@pytest.fixture(autouse=True)
def _metrics_reset():
    StructuredResolutionMetrics.reset()
    yield
    StructuredResolutionMetrics.reset()


def test_json_valid_accepted() -> None:
    sig, errs = parse_llm_resolution_json_string(
        '{"resolution_type":"off_topic","confidence":0.9,"target_action_type":null,'
        '"reason":"yield question","extracted_entities":{}}'
    )
    assert sig is not None and not errs
    assert sig.resolution_type == "off_topic"


def test_unknown_key_refused() -> None:
    sig, errs = parse_llm_resolution_json_any(
        {
            "resolution_type": "ambiguous",
            "confidence": 0.5,
            "target_action_type": None,
            "reason": "x",
            "extracted_entities": {},
            "should_cancel": True,
        }
    )
    assert sig is None
    assert errs


def test_free_text_refused() -> None:
    sig, errs = parse_llm_resolution_json_string("Bonjour, je suis un modèle")
    assert sig is None
    assert errs


def test_resolution_type_invalid_refused() -> None:
    payload = {
        "resolution_type": "buy_everything",
        "confidence": 0.9,
        "reason": "",
        "extracted_entities": {},
    }
    sig, errs = parse_llm_resolution_json_any(payload)
    assert sig is None


def test_confidence_out_of_range_refused() -> None:
    payload = {
        "resolution_type": "no_active_action",
        "confidence": 1.5,
        "reason": "",
        "extracted_entities": {},
    }
    sig, errs = parse_llm_resolution_json_any(payload)
    assert sig is None


def test_fence_stripped() -> None:
    inner = (
        '{"resolution_type":"same_action_continuation",'
        '"confidence":0.8,"target_action_type":null,"reason":"",'
        '"extracted_entities":{}}'
    )
    raw = f"```json\n{inner}\n```"
    assert strip_llm_json_fences(raw) == inner


def test_backend_adapter_no_should_flags_from_llm() -> None:
    sig = LLMConversationResolutionSignal(
        resolution_type="cancel_requested",
        confidence=1.0,
        target_action_type=None,
        reason="stop",
        extracted_entities={},
    )
    res = build_resolution_result_from_llm_signal(sig)
    assert res.should_cancel_active_draft
    assert res.should_keep_active_draft is False


@patch(
    "services.assistance.conversation_resolution.persist_conversation_resolution_audit"
)
@patch(
    "services.assistance.conversation_resolution_llm.persist_invalid_llm_resolution_audit",
    return_value=None,
)
@patch(
    "services.assistance.conversation_resolution.cancel_active_action_drafts",
    return_value=2,
)
def test_maybe_apply_cancel_from_valid_json(_canc: MagicMock, _inv: MagicMock, _pa: MagicMock) -> None:
    db = MagicMock()
    conv = uuid4()
    pend = {"action_type": "crypto_buy", "action_draft_id": str(uuid4())}
    payload = '{"resolution_type":"cancel_requested","confidence":0.99,"target_action_type":null,"reason":"x","extracted_entities":{}}'
    out = maybe_apply_llm_resolution(
        db,
        conversation_id=conv,
        raw_llm_output=payload,
        active_action_snapshot=pend,
        min_confidence=0.0,
    )
    assert out.validated and out.applied
    assert out.outcome is not None
    assert out.outcome.lifecycle_decision == "cancelled"
    _canc.assert_called()


@patch(
    "services.assistance.conversation_resolution.persist_conversation_resolution_audit"
)
@patch(
    "services.assistance.conversation_resolution_llm.persist_invalid_llm_resolution_audit",
    return_value=None,
)
@patch(
    "services.assistance.conversation_resolution.supersede_previous_drafts",
    return_value=1,
)
def test_maybe_apply_new_action_supersede(_sup: MagicMock, _inv: MagicMock, _pa: MagicMock) -> None:
    db = MagicMock()
    conv = uuid4()
    payload = '{"resolution_type":"new_action_detected","confidence":1.0,"target_action_type":"crypto_buy","reason":"switch","extracted_entities":{}}'
    out = maybe_apply_llm_resolution(
        db,
        conversation_id=conv,
        raw_llm_output=payload,
        active_action_snapshot={"action_type": "crypto_buy"},
        min_confidence=0.0,
    )
    assert out.applied
    assert out.outcome and out.outcome.lifecycle_decision == "superseded"
    _sup.assert_called()


@patch(
    "services.assistance.conversation_resolution.persist_conversation_resolution_audit"
)
@patch(
    "services.assistance.conversation_resolution_llm.persist_invalid_llm_resolution_audit",
    return_value=None,
)
def test_maybe_apply_invalid_no_lifecycle_calls(_inv: MagicMock, _pa: MagicMock) -> None:
    with patch(
        "services.assistance.conversation_resolution.cancel_active_action_drafts"
    ) as canc:
        with patch(
            "services.assistance.conversation_resolution.supersede_previous_drafts"
        ) as sup:
            db = MagicMock()
            conv = uuid4()
            out = maybe_apply_llm_resolution(
                db,
                conversation_id=conv,
                raw_llm_output="not-json",
                min_confidence=0.0,
            )
            assert out.validated is False
            canc.assert_not_called()
            sup.assert_not_called()


@patch(
    "services.assistance.conversation_resolution.persist_conversation_resolution_audit"
)
@patch(
    "services.assistance.conversation_resolution_llm.persist_invalid_llm_resolution_audit",
    return_value=None,
)
def test_maybe_apply_low_confidence_no_cancel(
    _inv: MagicMock, _pa: MagicMock
) -> None:
    with patch(
        "services.assistance.conversation_resolution.cancel_active_action_drafts"
    ) as canc:
        db = MagicMock()
        conv = uuid4()
        payload = (
            '{"resolution_type":"cancel_requested","confidence":0.1,'
            '"reason":"","extracted_entities":{}}'
        )
        out = maybe_apply_llm_resolution(
            db,
            conversation_id=conv,
            raw_llm_output=payload,
            min_confidence=0.5,
        )
        assert out.validated is True and out.applied is False
        assert out.low_confidence_fallback
        canc.assert_not_called()
