"""Tests unitaires pour ``infer_slot_attributions_v0`` (heuristique admin)."""

from __future__ import annotations

from services.assistance.runtime_debug_timeline import infer_slot_attributions_v0


def test_infer_amount_from_user_text_eur():
    out = infer_slot_attributions_v0(
        user_plain="Je veux investir 1500 € en BTC",
        tool_traces=[],
        draft_diff_entries=[],
    )
    assert out["_engine"] == "infer_slot_attributions_v0"
    slot = out["slots"]["amount_from"]
    assert slot["source"] == "user_explicit_in_text"
    assert slot["value"] == 1500.0
    assert slot["confidence"] >= 0.8


def test_infer_amount_merge_crypto_buy_intake_when_merge_sources():
    out = infer_slot_attributions_v0(
        user_plain="acheter du bitcoin",
        tool_traces=[
            {
                "tool_name": "crypto_buy_start",
                "result_summary": {"merge_sources": ["pending_action"]},
            }
        ],
        draft_diff_entries=[
            {"field": "amount_from", "before": None, "after": 1000.0}
        ],
    )
    slot = out["slots"]["amount_from"]
    assert slot["source"] == "merge_crypto_buy_intake"
    assert slot["value"] == 1000.0


def test_infer_amount_unknown_when_no_tool_trace():
    out = infer_slot_attributions_v0(
        user_plain="oui continue",
        tool_traces=[],
        draft_diff_entries=[
            {"field": "amount_from", "before": None, "after": 500.0}
        ],
    )
    slot = out["slots"]["amount_from"]
    assert slot["source"] == "unknown_injection"
    assert slot["value"] == 500.0
