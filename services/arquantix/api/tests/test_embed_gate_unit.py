"""Tests — `embed_gate.gate_embeds_for_ui_experience` (stress / stop_pushing)."""

from __future__ import annotations

import pytest

from services.assistance.embed_gate import (
    PROMOTIONAL_EMBED_TYPES,
    gate_embeds_for_ui_experience,
)


def _card(t: str, **extra: object) -> dict:
    return {"type": t, **extra}


class TestGateEmbedsBasics:
    def test_none_and_empty(self):
        assert gate_embeds_for_ui_experience(None, cognitive_state=None, objective=None) == []
        assert gate_embeds_for_ui_experience([], cognitive_state=None, objective=None) == []

    def test_no_stress_passes_through(self):
        embeds = [
            _card("instrument_detail_card", id=1),
            _card("transaction_detail", id=2),
        ]
        out = gate_embeds_for_ui_experience(
            embeds,
            cognitive_state={"emotional_intent": "neutral"},
            objective={"stop_pushing": False},
        )
        assert len(out) == 2
        assert out[0]["type"] == "instrument_detail_card"


class TestGateEmbedsStripPromo:
    @pytest.mark.parametrize("ptype", sorted(PROMOTIONAL_EMBED_TYPES))
    def test_stop_pushing_strips_discovery_or_promo_types(self, ptype: str):
        embeds = [_card(ptype), _card("transaction_detail")]
        out = gate_embeds_for_ui_experience(
            embeds,
            cognitive_state=None,
            objective={"stop_pushing": True},
        )
        assert len(out) == 1
        assert out[0]["type"] == "transaction_detail"

    def test_invest_confirmation_never_stripped(self):
        embeds = [_card("invest_confirmation_draft", id="x"), _card("featured_articles_list")]
        out = gate_embeds_for_ui_experience(
            embeds,
            cognitive_state=None,
            objective={"stop_pushing": True},
        )
        assert len(out) == 1
        assert out[0]["type"] == "invest_confirmation_draft"

    def test_top_movers_treated_as_info_not_stripped(self):
        embeds = [_card("top_movers_crypto"), _card("bundle_detail_card")]
        out = gate_embeds_for_ui_experience(
            embeds,
            cognitive_state=None,
            objective={"stop_pushing": True},
        )
        ts = [e["type"] for e in out]
        assert "top_movers_crypto" in ts
        assert "bundle_detail_card" not in ts

    def test_fear_also_triggers_strip_even_without_stop_pushing(self):
        embeds = [_card("featured_articles_list"), _card("portfolio_allocation_donut")]
        out = gate_embeds_for_ui_experience(
            embeds,
            cognitive_state={"emotional_intent": "fear"},
            objective=None,
        )
        assert len(out) == 1
        assert out[0]["type"] == "portfolio_allocation_donut"


class TestGateEmbedsCap:
    def test_fear_caps_non_promo_to_one_prefers_transaction(self):
        embeds = [
            _card("portfolio_allocation_donut"),
            _card("transaction_detail"),
            _card("other_widget"),
        ]
        out = gate_embeds_for_ui_experience(
            embeds,
            cognitive_state={"emotional_intent": "anger"},
            objective={"stop_pushing": False},
        )
        assert len(out) == 1
        assert out[0]["type"] == "transaction_detail"

    def test_stop_pushing_only_caps_to_two(self):
        embeds = [
            _card("portfolio_allocation_donut"),
            _card("transaction_detail"),
            _card("other_widget"),
        ]
        out = gate_embeds_for_ui_experience(
            embeds,
            cognitive_state={"emotional_intent": "neutral"},
            objective={"stop_pushing": True},
        )
        types = [e["type"] for e in out]
        assert len(out) == 2
        assert "transaction_detail" in types
        assert "portfolio_allocation_donut" in types
