"""Tests unitaires Phase 2 wiki v1.4 patch — slot mémoire `current_topic`.

Couvre :
  * `infer_topic_from_tool_call` : matching par tool_name, validation
    des champs requis, return None sur tool non-ancrant.
  * `render_topic_for_prompt` : libellés par kind, gestion des cas vides.
  * `get_topic` / `set_topic` / `clear_topic` : path defensive (conv
    inexistante, slot mal formé).
  * `TOPIC_ANCHORING_TOOLS` : périmètre attendu (whitelist).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from services.assistance.conversation_topic import (
    DEFAULT_TOPIC_CONFIDENCE,
    TOPIC_ANCHORING_TOOLS,
    clear_topic,
    get_topic,
    infer_topic_from_tool_call,
    render_topic_for_prompt,
    set_topic,
)


# ─────────────────────────────────────────────────────────────────────
# Périmètre TOPIC_ANCHORING_TOOLS
# ─────────────────────────────────────────────────────────────────────


class TestAnchoringToolsPerimeter:
    def test_includes_show_bundle_detail(self):
        assert TOPIC_ANCHORING_TOOLS["show_bundle_detail"] == "vancelian_product"

    def test_includes_show_instrument_card(self):
        assert TOPIC_ANCHORING_TOOLS["show_instrument_card"] == "instrument"

    def test_excludes_list_tools(self):
        """Les tools qui retournent des LISTES (`show_crypto_bundles`,
        `select_wiki_pages`) n'ancrent rien — c'est de l'exploration."""
        assert "show_crypto_bundles" not in TOPIC_ANCHORING_TOOLS
        assert "select_wiki_pages" not in TOPIC_ANCHORING_TOOLS

    def test_excludes_orchestration_tools(self):
        for t in ("consult_specialist", "handoff_to_agent", "ask_user_question"):
            assert t not in TOPIC_ANCHORING_TOOLS


# ─────────────────────────────────────────────────────────────────────
# infer_topic_from_tool_call — cas par tool
# ─────────────────────────────────────────────────────────────────────


class TestInferShowBundleDetail:
    def test_success_extracts_product_code(self):
        topic = infer_topic_from_tool_call(
            tool_name="show_bundle_detail",
            tool_args={"product_code": "TOP_5"},
            tool_result={
                "bundle": {
                    "id": "uuid-x",
                    "product_code": "TOP_5",
                    "name": "Crypto Top 5",
                },
                "embed_emitted": True,
            },
            agent_id="product",
            turn_index=4,
        )
        assert topic is not None
        assert topic["kind"] == "vancelian_product"
        assert topic["product_code"] == "TOP_5"
        assert topic["agent_owner"] == "product"
        assert topic["set_at_turn"] == 4
        assert topic["set_by_tool"] == "show_bundle_detail"
        assert topic["confidence"] == DEFAULT_TOPIC_CONFIDENCE
        assert "set_at" in topic and topic["set_at"]

    def test_uppercases_product_code(self):
        topic = infer_topic_from_tool_call(
            tool_name="show_bundle_detail",
            tool_args={"product_code": "top_5"},
            tool_result={"bundle": {"product_code": "top_5"}},
            agent_id="product",
            turn_index=4,
        )
        assert topic is not None
        assert topic["product_code"] == "TOP_5"

    def test_missing_bundle_returns_none(self):
        """Échec du tool (bundle non trouvé) → pas de topic set."""
        topic = infer_topic_from_tool_call(
            tool_name="show_bundle_detail",
            tool_args={"product_code": "UNKNOWN"},
            tool_result={"error": "bundle_not_found"},
            agent_id="product",
            turn_index=4,
        )
        assert topic is None

    def test_empty_product_code_returns_none(self):
        topic = infer_topic_from_tool_call(
            tool_name="show_bundle_detail",
            tool_args={},
            tool_result={"bundle": {"product_code": ""}},
            agent_id="product",
            turn_index=4,
        )
        assert topic is None


class TestInferShowInstrumentCard:
    def test_extracts_symbol_uppercased(self):
        topic = infer_topic_from_tool_call(
            tool_name="show_instrument_card",
            tool_args={"symbol": "btc"},
            tool_result={"symbol": "btc", "embed_emitted": True},
            agent_id="product",
            turn_index=2,
        )
        assert topic is not None
        assert topic["kind"] == "instrument"
        assert topic["instrument_symbol"] == "BTC"

    def test_missing_symbol_returns_none(self):
        topic = infer_topic_from_tool_call(
            tool_name="show_instrument_card",
            tool_args={},
            tool_result={"error": "instrument_not_found"},
            agent_id="product",
            turn_index=2,
        )
        assert topic is None


class TestInferReadWikiPage:
    def test_extracts_category_and_slug(self):
        topic = infer_topic_from_tool_call(
            tool_name="read_wiki_page",
            tool_args={"slug": "deposit_sepa"},
            tool_result={
                "category": "transfers-cards",
                "slug": "deposit_sepa",
                "title": "SEPA deposit",
                "body": "...",
            },
            agent_id="compliance",
            turn_index=1,
        )
        assert topic is not None
        assert topic["kind"] == "topic_other"
        assert topic["wiki_category"] == "transfers-cards"
        assert topic["wiki_slug"] == "deposit_sepa"


class TestInferNonAnchoringTool:
    def test_show_crypto_bundles_returns_none(self):
        """`show_crypto_bundles` retourne une LISTE → aucune ancre."""
        topic = infer_topic_from_tool_call(
            tool_name="show_crypto_bundles",
            tool_args={},
            tool_result={"bundles_count": 5, "embed_emitted": True},
            agent_id="product",
            turn_index=1,
        )
        assert topic is None

    def test_consult_specialist_returns_none(self):
        topic = infer_topic_from_tool_call(
            tool_name="consult_specialist",
            tool_args={"target_agent": "advisor", "question": "..."},
            tool_result={"interrupt_with_consult": True},
            agent_id="product",
            turn_index=1,
        )
        assert topic is None

    def test_unknown_tool_returns_none(self):
        topic = infer_topic_from_tool_call(
            tool_name="totally_made_up_tool",
            tool_args={},
            tool_result={"ok": True},
            agent_id="product",
            turn_index=1,
        )
        assert topic is None

    def test_non_dict_result_returns_none(self):
        topic = infer_topic_from_tool_call(
            tool_name="show_bundle_detail",
            tool_args={},
            tool_result="not a dict",  # type: ignore[arg-type]
            agent_id="product",
            turn_index=1,
        )
        assert topic is None


# ─────────────────────────────────────────────────────────────────────
# render_topic_for_prompt
# ─────────────────────────────────────────────────────────────────────


class TestRenderTopicForPrompt:
    def test_vancelian_product(self):
        text = render_topic_for_prompt({
            "kind": "vancelian_product",
            "product_code": "TOP_5",
            "agent_owner": "product",
        })
        assert "TOP_5" in text
        assert "produit Vancelian" in text
        assert "agent owner: product" in text

    def test_instrument(self):
        text = render_topic_for_prompt({
            "kind": "instrument",
            "instrument_symbol": "BTC",
            "agent_owner": "product",
        })
        assert "BTC" in text
        assert "instrument" in text

    def test_topic_other_with_wiki_slug(self):
        text = render_topic_for_prompt({
            "kind": "topic_other",
            "wiki_slug": "deposit_sepa",
            "agent_owner": "compliance",
        })
        assert "deposit_sepa" in text
        assert "agent owner: compliance" in text

    def test_none_returns_empty(self):
        assert render_topic_for_prompt(None) == ""

    def test_invalid_dict_returns_empty(self):
        assert render_topic_for_prompt({}) == ""
        assert render_topic_for_prompt({"kind": "vancelian_product"}) == ""

    def test_unknown_kind_returns_empty(self):
        assert (
            render_topic_for_prompt(
                {"kind": "alien_kind", "agent_owner": "product"}
            )
            == ""
        )


# ─────────────────────────────────────────────────────────────────────
# get / set / clear — defensive
# ─────────────────────────────────────────────────────────────────────


class TestPersistenceDefensive:
    def test_get_topic_returns_none_if_conv_missing(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = None
        assert get_topic(db, "missing-id") is None

    def test_get_topic_returns_none_if_slot_not_dict(self):
        db = MagicMock()
        conv = MagicMock()
        conv.current_topic = "not a dict"
        db.query.return_value.filter.return_value.one_or_none.return_value = conv
        assert get_topic(db, "id") is None

    def test_get_topic_returns_dict_copy(self):
        db = MagicMock()
        conv = MagicMock()
        conv.current_topic = {
            "kind": "vancelian_product",
            "product_code": "TOP_5",
            "agent_owner": "product",
        }
        db.query.return_value.filter.return_value.one_or_none.return_value = conv
        topic = get_topic(db, "id")
        assert topic is not None
        assert topic["product_code"] == "TOP_5"
        # Mutation côté caller ne contamine pas la session.
        topic["product_code"] = "MUTATED"
        assert conv.current_topic["product_code"] == "TOP_5"

    def test_set_topic_writes_and_commits(self):
        db = MagicMock()
        conv = MagicMock()
        conv.current_topic = None
        db.query.return_value.filter.return_value.one_or_none.return_value = conv
        new_topic = {
            "kind": "vancelian_product",
            "product_code": "TOP_5",
            "agent_owner": "product",
            "set_at_turn": 1,
            "set_by_tool": "show_bundle_detail",
            "confidence": 0.95,
            "set_at": "2026-05-04T18:00:00Z",
        }
        set_topic(db, "id", new_topic)
        assert conv.current_topic == new_topic
        db.commit.assert_called_once()

    def test_set_topic_no_commit_when_flag_false(self):
        db = MagicMock()
        conv = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = conv
        set_topic(db, "id", {"kind": "instrument"}, commit=False)
        db.commit.assert_not_called()

    def test_clear_topic_sets_none(self):
        db = MagicMock()
        conv = MagicMock()
        conv.current_topic = {"kind": "vancelian_product"}
        db.query.return_value.filter.return_value.one_or_none.return_value = conv
        clear_topic(db, "id")
        assert conv.current_topic is None
        db.commit.assert_called_once()

    def test_set_topic_silent_if_conv_missing(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = None
        # Doit pas crash — c'est best-effort.
        set_topic(db, "missing", {"kind": "vancelian_product"})
        db.commit.assert_not_called()
