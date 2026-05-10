"""Tests — ``crypto_investment_intent`` (logique pure + flow JSON)."""

from __future__ import annotations

from services.assistance.agents.runtime.agent_loop import (
    _filter_crypto_intent_routing_gate,
)
from services.assistance.agents.tools.action.crypto_investment_intent_logic import (
    clarification_backend_options_from_source_items,
    crypto_intent_target_asset_supersedes_active_draft,
    infer_crypto_intent_confirmation_from_text,
    infer_stage_from_slots,
    infer_target_candidate_symbol_for_crypto_intent,
    items_for_source_account_clarification,
    match_source_account,
    merge_slots_payload,
)
from services.assistance.crypto_investment_intent_flow_doc import (
    load_crypto_investment_intent_flow_v1,
)


def test_flow_loader_v1():
    doc = load_crypto_investment_intent_flow_v1()
    assert doc.flow_id == "crypto_investment_intent"
    assert doc.execution_policy.ai_can_execute_order is False


def test_infer_target_candidate_from_symbol_or_raw():
    assert infer_target_candidate_symbol_for_crypto_intent(slots_fragment={"symbol": "eth"}) == "ETH"
    assert infer_target_candidate_symbol_for_crypto_intent(
        slots_fragment={"raw": "bitcoin"},
    ) == "BTC"
    assert infer_target_candidate_symbol_for_crypto_intent(slots_fragment={}) is None


def test_supersedes_when_candidate_target_changes():
    prev = {
        "target_asset": {"symbol": "BTC", "raw": "bitcoin"},
        "source_account": {},
        "amount": {},
    }
    patch_conflict = {"target_asset": {"symbol": "ETH"}, "source_account": {}, "amount": {}}
    assert crypto_intent_target_asset_supersedes_active_draft(
        prev_slots=prev,
        patch_slots=patch_conflict,
    )
    patch_no_target = {"target_asset": {}, "source_account": {"raw": "euro"}, "amount": {}}
    assert not crypto_intent_target_asset_supersedes_active_draft(
        prev_slots=prev,
        patch_slots=patch_no_target,
    )


def test_infer_stage_pending_until_three_slots():
    slots = {
        "target_asset": {"raw": "bitcoin", "raw_provenance": "llm_extracted"},
        "source_account": {},
        "amount": {},
    }
    assert infer_stage_from_slots(slots) == "draft_pending_slots"


def test_infer_stage_ready_when_complete_raw():
    slots = {
        "target_asset": {"raw": "bitcoin"},
        "source_account": {"raw": "compte euro"},
        "amount": {"raw": "1000 €", "value": 1000.0, "currency": "EUR"},
    }
    assert infer_stage_from_slots(slots) == "draft_ready_for_backend_validation"


def test_merge_slots_deep():
    base = {
        "target_asset": {"raw": "eth", "confidence": 0.5},
        "source_account": {},
        "amount": {},
    }
    patch = {"target_asset": {"raw": "Bitcoin", "confidence": 0.92}}
    out = merge_slots_payload(base, patch)
    assert out["target_asset"]["raw"] == "Bitcoin"
    assert out["target_asset"]["confidence"] == 0.92


def test_match_source_two_eur_rows_ambiguous():
    items = [
        {
            "account_key": "fiat",
            "label": "Compte Euro courant",
            "currency": "EUR",
            "source_kind": "fiat",
        },
        {
            "account_key": "fiat_livret",
            "label": "Livret Euro",
            "currency": "EUR",
            "source_kind": "fiat",
        },
    ]
    row, status, errs = match_source_account("paiement depuis mon compte euro", items)
    assert row is None
    assert status == "ambiguous"
    assert any("eur" in e for e in errs)


def test_match_source_single_eur_ok():
    items = [
        {
            "account_key": "fiat",
            "label": "Compte Euro",
            "balance": 2000.0,
            "currency": "EUR",
            "source_kind": "fiat",
        },
    ]
    row, status, errs = match_source_account("compte euro", items)
    assert status == "resolved"
    assert row is not None
    assert row["account_key"] == "fiat"
    assert not errs


def test_skip_empty_source_raw():
    row, status, errs = match_source_account("   ", [{"account_key": "fiat"}])
    assert status == "skipped"
    assert row is None


class _FakeToolModule:
    def __init__(self, name: str) -> None:
        self.SPEC = {"type": "function", "function": {"name": name}}


def test_routing_gate_strips_start_below_confidence_floor():
    start = _FakeToolModule("crypto_investment_intent_start")
    resolve = _FakeToolModule("crypto_investment_intent_resolve")
    confirm = _FakeToolModule("crypto_investment_intent_confirm")
    mem = {
        "orchestration": {
            "transaction_kind": "crypto_investment_intent",
            "routing_confidence": 0.41,
        },
    }
    out = _filter_crypto_intent_routing_gate(
        [start, resolve, confirm],
        memory_state=mem,
        conversation_id="00000000-0000-0000-0000-000000000001",
    )
    names = [(m.SPEC["function"]["name"]) for m in out]
    assert "crypto_investment_intent_start" not in names
    assert "crypto_investment_intent_resolve" in names
    assert "crypto_investment_intent_confirm" in names


def test_routing_gate_keeps_start_at_or_above_floor():
    start = _FakeToolModule("crypto_investment_intent_start")
    mem = {
        "orchestration": {
            "transaction_kind": "crypto_investment_intent",
            "routing_confidence": 0.6,
        },
    }
    out = _filter_crypto_intent_routing_gate([start], memory_state=mem, conversation_id="c")
    assert len(out) == 1


def test_match_via_selected_option_id():
    items = [{"account_key": "fiat", "label": "EUR", "source_kind": "fiat"}]
    row, status, errs = match_source_account(
        None,
        items,
        selected_option_id="fiat",
    )
    assert status == "resolved"
    assert row["account_key"] == "fiat"
    assert not errs


def test_infer_confirmation_phrases():
    assert infer_crypto_intent_confirmation_from_text("oui") == "confirm"
    assert infer_crypto_intent_confirmation_from_text(" vas y ") == "confirm"
    assert infer_crypto_intent_confirmation_from_text("non merci") == "decline"
    assert infer_crypto_intent_confirmation_from_text("") == "unknown"


def test_qcm_options_stable_ids_and_subset():
    items = [
        {"account_key": "a", "label": "Euro A"},
        {"account_key": "b", "label": "Euro B"},
    ]
    errs = ["plusieurs_sources_eur_non_resolues"]
    sub = items_for_source_account_clarification(errors=errs, items=items)
    opts = clarification_backend_options_from_source_items(items, restrict_to=sub)
    assert {o["option_id"] for o in opts} == {"a", "b"}
