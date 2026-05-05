"""Tests unitaires Phase 2 wiki v1.4 — tool `show_bundle_detail` (agent
`product`, autonomy L0).

Couvre :
  * SPEC : agent_id, autonomy_level, name, parameters (product_code +
    bundle_id, aucun required strict)
  * `execute()` :
    - cas nominal product_code → embed `bundle_detail_card` complet
    - cas nominal bundle_id → embed `bundle_detail_card` complet
    - product_code prioritaire si les deux sont fournis
    - cas catalogue vide → `error: no_active_bundle`
    - cas erreur DB → `error: catalog_unavailable`
    - cas bundle_not_found → `error` + `available_product_codes`
    - cas missing_identifier (ni product_code, ni bundle_id)
    - cas allocation vide / partielle (skip alloc sans symbol)
  * Helper `_summarize_allocations` : edge cases
  * Action CTA catalog : réutilise `view_bundle_detail` + `invest_bundle`
  * Guard-rail anti-hallucination : `show_bundle_detail` est reconnu
    comme un tool de lecture (équivalent `show_instrument_card`).
  * Registry : `show_bundle_detail` exposé à l'agent product.

Tous les tests utilisent un mock du `CatalogService.get_public_catalog`
(pas de DB).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.product import show_bundle_detail
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.portfolio_engine.products.catalog import (
    AllocationSummaryItem,
    ProductCatalogItem,
)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _ctx() -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=None,
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="product",
        conversation_id=str(uuid4()),
        iteration=1,
        audit_session_id=str(uuid4()),
        correlation_id=str(uuid4()),
    )


def _make_alloc(
    *,
    instrument_code: str = "BTC",
    instrument_name: str = "Bitcoin",
    asset_symbol: str = "BTC",
    target_weight: str = "0.50",
) -> AllocationSummaryItem:
    return AllocationSummaryItem(
        instrument_id=uuid4(),
        instrument_code=instrument_code,
        instrument_name=instrument_name,
        asset_symbol=asset_symbol,
        target_weight=Decimal(target_weight),
    )


def _make_bundle(
    *,
    name: str = "Top 5",
    product_code: str = "TOP_5",
    description: str | None = "Les 5 cryptos majeures",
    risk_label: str | None = "high",
    base_currency: str = "EUR",
    entry_asset_default: str | None = "USDC",
    allocations: list[AllocationSummaryItem] | None = None,
    product_id=None,
) -> ProductCatalogItem:
    return ProductCatalogItem(
        id=product_id or uuid4(),
        product_code=product_code,
        name=name,
        description=description,
        product_type="crypto_bundle",
        risk_label=risk_label,
        base_currency=base_currency,
        status="active",
        entry_asset_default=entry_asset_default,
        entry_assets_allowed=["USDC", "EUR"],
        allocations=allocations or [
            _make_alloc(asset_symbol="BTC", target_weight="0.60"),
            _make_alloc(
                instrument_code="ETH",
                instrument_name="Ethereum",
                asset_symbol="ETH",
                target_weight="0.40",
            ),
        ],
        available_rebalance_frequencies=["weekly", "monthly"],
        metadata={},
    )


# ─────────────────────────────────────────────────────────────────────
# SPEC
# ─────────────────────────────────────────────────────────────────────


class TestShowBundleDetailSpec:
    def test_spec_basic_shape(self):
        spec = show_bundle_detail.SPEC
        assert spec["type"] == "function"
        assert spec["agent_id"] == "product"
        assert spec["autonomy_level"] == "L0"

    def test_spec_function_name(self):
        assert (
            show_bundle_detail.SPEC["function"]["name"]
            == "show_bundle_detail"
        )

    def test_spec_accepts_product_code_or_bundle_id(self):
        params = show_bundle_detail.SPEC["function"]["parameters"]
        assert params.get("type") == "object"
        assert params.get("additionalProperties") is False
        props = params.get("properties") or {}
        assert "product_code" in props
        assert props["product_code"]["type"] == "string"
        assert "bundle_id" in props
        assert props["bundle_id"]["type"] == "string"
        # Pas de required strict — la validation se fait au runtime
        # (au moins un des deux doit être fourni).
        assert not params.get("required")

    def test_spec_description_warns_against_misuse(self):
        """Le LLM doit savoir qu'il faut PRÉFÉRER show_crypto_bundles
        pour les listes — sinon il va spammer show_bundle_detail."""
        desc = show_bundle_detail.SPEC["function"]["description"].lower()
        assert "show_crypto_bundles" in desc or "plusieurs bundles" in desc


# ─────────────────────────────────────────────────────────────────────
# execute() — cas nominal
# ─────────────────────────────────────────────────────────────────────


class TestShowBundleDetailNominal:
    def test_product_code_nominal_emits_embed(self):
        bundle_id = uuid4()
        bundle = _make_bundle(product_id=bundle_id, product_code="TOP_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            result = show_bundle_detail.execute(ctx, product_code="TOP_5")
        assert result["embed_emitted"] is True
        assert result["bundle"]["id"] == str(bundle_id)
        assert result["bundle"]["product_code"] == "TOP_5"
        # Allocations summary reflète les pourcentages réels.
        assert "60% BTC" in (result["bundle"]["allocations_summary"] or "")
        assert "40% ETH" in (result["bundle"]["allocations_summary"] or "")
        # Embed pushé.
        assert len(ctx.embeds_to_emit) == 1
        embed = ctx.embeds_to_emit[0]
        assert embed["type"] == "bundle_detail_card"
        assert embed["id"] == str(bundle_id)
        assert embed["product_code"] == "TOP_5"
        assert len(embed["allocations"]) == 2

    def test_product_code_is_case_insensitive(self):
        bundle = _make_bundle(product_code="TOP_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            result = show_bundle_detail.execute(ctx, product_code="top_5")
        assert result["embed_emitted"] is True
        assert result["bundle"]["product_code"] == "TOP_5"

    def test_bundle_id_nominal_emits_embed(self):
        bundle_id = uuid4()
        bundle = _make_bundle(product_id=bundle_id, product_code="ALT_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            result = show_bundle_detail.execute(
                ctx, bundle_id=str(bundle_id)
            )
        assert result["embed_emitted"] is True
        assert result["bundle"]["id"] == str(bundle_id)
        assert result["bundle"]["product_code"] == "ALT_5"

    def test_product_code_takes_priority_over_id(self):
        """Si les deux sont fournis et matchent des bundles différents,
        product_code prime (c'est ce que connait le client). En
        pratique, le LLM ne devrait pas mélanger, mais on garantit
        un comportement déterministe."""
        b_top = _make_bundle(product_code="TOP_5", product_id=uuid4())
        b_alt = _make_bundle(product_code="ALT_5", product_id=uuid4())
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[b_top, b_alt],
        ):
            result = show_bundle_detail.execute(
                ctx, product_code="TOP_5", bundle_id=str(b_alt.id)
            )
        # Le code wins → on récupère TOP_5 (pas ALT_5).
        assert result["bundle"]["product_code"] == "TOP_5"

    def test_emits_actions_view_and_invest(self):
        bundle = _make_bundle(product_code="TOP_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            show_bundle_detail.execute(ctx, product_code="TOP_5")
        actions = ctx.embeds_to_emit[0]["actions"]
        kinds = {a["kind"] for a in actions}
        assert kinds == {"view_bundle_detail", "invest_bundle"}
        # Les deep-links sont bien construits avec le bundle_id.
        bid = str(bundle.id)
        for a in actions:
            assert bid in (a.get("deep_link") or "")


# ─────────────────────────────────────────────────────────────────────
# execute() — edge cases
# ─────────────────────────────────────────────────────────────────────


class TestShowBundleDetailEdgeCases:
    def test_missing_identifier_returns_error(self):
        ctx = _ctx()
        result = show_bundle_detail.execute(ctx)
        assert result["error"] == "missing_identifier"
        assert ctx.embeds_to_emit == []

    def test_empty_strings_treated_as_missing(self):
        ctx = _ctx()
        result = show_bundle_detail.execute(
            ctx, product_code="   ", bundle_id=""
        )
        assert result["error"] == "missing_identifier"

    def test_empty_catalog_returns_error(self):
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[],
        ):
            result = show_bundle_detail.execute(ctx, product_code="TOP_5")
        assert result["error"] == "no_active_bundle"
        assert result["embed_emitted"] is False
        assert ctx.embeds_to_emit == []

    def test_catalog_error_returns_unavailable(self):
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            side_effect=RuntimeError("boom"),
        ):
            result = show_bundle_detail.execute(ctx, product_code="TOP_5")
        assert result == {"error": "catalog_unavailable"}

    def test_not_found_returns_available_codes(self):
        b1 = _make_bundle(product_code="TOP_5")
        b2 = _make_bundle(product_code="ALT_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[b1, b2],
        ):
            result = show_bundle_detail.execute(ctx, product_code="BOGUS")
        assert result["error"] == "bundle_not_found"
        assert "TOP_5" in result["available_product_codes"]
        assert "ALT_5" in result["available_product_codes"]
        assert ctx.embeds_to_emit == []

    def test_skips_allocation_with_empty_symbol(self):
        bundle = _make_bundle(
            allocations=[
                _make_alloc(asset_symbol="BTC", target_weight="0.70"),
                _make_alloc(asset_symbol="", target_weight="0.30"),
            ],
            product_code="TOP_5",
        )
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_bundle_detail."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            show_bundle_detail.execute(ctx, product_code="TOP_5")
        allocs = ctx.embeds_to_emit[0]["allocations"]
        assert len(allocs) == 1
        assert allocs[0]["symbol"] == "BTC"


# ─────────────────────────────────────────────────────────────────────
# Helper interne `_summarize_allocations`
# ─────────────────────────────────────────────────────────────────────


class TestSummarizeAllocations:
    def test_empty_returns_none(self):
        assert show_bundle_detail._summarize_allocations([]) is None

    def test_zero_weights_returns_none(self):
        assert (
            show_bundle_detail._summarize_allocations(
                [{"symbol": "BTC", "weight": 0.0}]
            )
            is None
        )

    def test_two_assets_pct_format(self):
        result = show_bundle_detail._summarize_allocations(
            [
                {"symbol": "BTC", "weight": 0.60},
                {"symbol": "ETH", "weight": 0.40},
            ]
        )
        assert result == "60% BTC, 40% ETH"


# ─────────────────────────────────────────────────────────────────────
# Registry + Guard-rail
# ─────────────────────────────────────────────────────────────────────


class TestShowBundleDetailRegistryAndGuardrail:
    def test_registered_for_product_agent(self):
        from services.assistance.agents.tools.registry import all_tool_names

        names = all_tool_names("product")
        assert "show_bundle_detail" in names

    def test_not_registered_for_other_agents(self):
        from services.assistance.agents.tools.registry import all_tool_names

        for agent in (
            "compliance",
            "compliance.transactional",
            "compliance.general",
            "advisor",
            "market",
        ):
            assert "show_bundle_detail" not in all_tool_names(agent), (
                f"show_bundle_detail leaked to agent={agent}"
            )

    def test_recognized_as_knowledge_read_tool(self):
        """Le guard-rail anti-hallucination doit reconnaître
        `show_bundle_detail` comme un tool de lecture sourcée DB
        (équivalent fonctionnel de `show_instrument_card`)."""
        from services.assistance.agents.runtime.agent_loop import (
            PRODUCT_KNOWLEDGE_READ_TOOLS,
        )

        assert "show_bundle_detail" in PRODUCT_KNOWLEDGE_READ_TOOLS
