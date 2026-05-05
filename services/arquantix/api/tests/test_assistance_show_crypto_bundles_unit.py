"""Tests unitaires Phase 2 wiki — tool `show_crypto_bundles` (agent
`product`, autonomy L0).

Couvre :
  * SPEC : agent_id, autonomy_level, name, description, parameters
  * `execute()` :
    - cas nominal 2 bundles → embed `crypto_bundles_card` complet
    - cas catalogue vide → bundles_count=0, embed_emitted=False, pas
      d'embed dans `ctx.embeds_to_emit`
    - cas erreur DB (CatalogService.get_public_catalog raise) →
      `error: catalog_unavailable`
    - cas trop de bundles → tronqué à `_MAX_BUNDLES`
    - cas allocation vide / partielle (skip alloc sans symbol)
    - cas erreur de paramètres deep-link (build_action retourne None) →
      le tool n'embarque pas l'action invalide mais n'échoue pas
  * Helper `_summarize_allocations` : edge cases (vide, weights nuls,
    arrondi)
  * Action CTA catalog : `view_bundle_detail` + `invest_bundle`
    correctement enregistrés (kind, deep_link, requires_param)
  * Guard-rail anti-hallucination : `show_crypto_bundles` est reconnu
    comme un tool de lecture (équivalent `show_instrument_card`)

Tous les tests utilisent un mock du `CatalogService.get_public_catalog`
pour ne pas dépendre de la DB. La logique de DB elle-même est testée
dans `test_portfolio_engine_products.py`.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.product import show_crypto_bundles
from services.assistance.agents.tools.shared.action_cta_catalog import (
    build_action,
    get_spec,
    is_available,
    is_known_deep_link,
    is_known_kind,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.portfolio_engine.products.catalog import (
    AllocationSummaryItem,
    ProductCatalogItem,
)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _ctx() -> ToolContext:
    """ToolContext minimal pour un agent product.

    DB est mockée — `show_crypto_bundles` n'utilise `ctx.db` que pour
    le passer à `CatalogService.get_public_catalog`, qu'on mocke
    aussi via patch.
    """
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
            _make_alloc(asset_symbol="BTC", target_weight="0.50"),
            _make_alloc(
                instrument_code="ETH",
                instrument_name="Ethereum",
                asset_symbol="ETH",
                target_weight="0.20",
            ),
        ],
        available_rebalance_frequencies=["weekly", "monthly"],
        metadata={},
    )


# ─────────────────────────────────────────────────────────────────────
# SPEC
# ─────────────────────────────────────────────────────────────────────


class TestShowCryptoBundlesSpec:
    def test_spec_basic_shape(self):
        spec = show_crypto_bundles.SPEC
        assert spec["type"] == "function"
        assert spec["agent_id"] == "product"
        assert spec["autonomy_level"] == "L0"

    def test_spec_function_name(self):
        assert (
            show_crypto_bundles.SPEC["function"]["name"]
            == "show_crypto_bundles"
        )

    def test_spec_optional_product_codes_param(self):
        """Le tool accepte un paramètre **optionnel** `product_codes`
        (liste de codes pour filtrer la liste). Sans paramètre, dump
        tout le catalogue public actif."""
        params = show_crypto_bundles.SPEC["function"]["parameters"]
        assert params.get("type") == "object"
        assert params.get("additionalProperties") is False
        # `product_codes` doit être déclaré comme array de strings.
        props = params.get("properties") or {}
        assert "product_codes" in props
        pc = props["product_codes"]
        assert pc.get("type") == "array"
        assert pc.get("items", {}).get("type") == "string"
        # Pas de `required` ou required vide (filtrage optionnel).
        assert not params.get("required")

    def test_spec_description_mentions_use_case(self):
        """Description guide le LLM — doit mentionner les triggers
        oraux fréquents pour qu'il appelle au bon moment."""
        desc = show_crypto_bundles.SPEC["function"]["description"]
        assert "bundles disponibles" in desc.lower() or "catalogue" in desc.lower()
        assert "investir" in desc.lower()


# ─────────────────────────────────────────────────────────────────────
# execute() — cas nominal
# ─────────────────────────────────────────────────────────────────────


class TestShowCryptoBundlesNominal:
    def test_returns_embed_for_two_bundles(self):
        """Cas nominal : 2 bundles publics actifs → 1 embed
        crypto_bundles_card avec 2 items + return summary."""
        b1_id = uuid4()
        b2_id = uuid4()
        b1 = _make_bundle(
            name="Top 2",
            product_code="TOP_2",
            description="Bitcoin et Ethereum",
            allocations=[
                _make_alloc(asset_symbol="BTC", target_weight="0.70"),
                _make_alloc(
                    asset_symbol="ETH",
                    instrument_name="Ethereum",
                    target_weight="0.30",
                ),
            ],
            product_id=b1_id,
        )
        b2 = _make_bundle(
            name="Top 5",
            product_code="TOP_5",
            allocations=[
                _make_alloc(asset_symbol="BTC", target_weight="0.50"),
                _make_alloc(
                    asset_symbol="ETH",
                    instrument_name="Ethereum",
                    target_weight="0.20",
                ),
                _make_alloc(
                    asset_symbol="XRP",
                    instrument_name="Ripple",
                    target_weight="0.10",
                ),
            ],
            product_id=b2_id,
        )
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[b1, b2],
        ):
            result = show_crypto_bundles.execute(ctx)

        assert result["embed_emitted"] is True
        assert result["bundles_count"] == 2
        # Un seul embed poussé.
        assert len(ctx.embeds_to_emit) == 1
        embed = ctx.embeds_to_emit[0]
        assert embed["type"] == "crypto_bundles_card"
        assert len(embed["bundles"]) == 2

    def test_embed_bundle_shape(self):
        """Vérifie le shape exact d'un bundle dans l'embed (clés et
        types) — contrat avec le client Flutter."""
        bid = uuid4()
        bundle = _make_bundle(product_id=bid)
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            show_crypto_bundles.execute(ctx)
        item = ctx.embeds_to_emit[0]["bundles"][0]
        assert item["id"] == str(bid)
        assert item["product_code"] == "TOP_5"
        assert item["name"] == "Top 5"
        assert item["description"] == "Les 5 cryptos majeures"
        assert item["risk_label"] == "high"
        assert item["base_currency"] == "EUR"
        assert item["entry_asset_default"] == "USDC"
        # Allocations normalisées en `{symbol, instrument_name, weight}`
        # avec symbol upper et weight float.
        assert isinstance(item["allocations"], list)
        assert len(item["allocations"]) == 2
        first = item["allocations"][0]
        assert first["symbol"] == "BTC"
        assert isinstance(first["weight"], float)
        assert first["weight"] == 0.50

    def test_embed_includes_two_actions(self):
        """Chaque bundle doit avoir 2 actions whitelistées :
        view_bundle_detail (tap card) + invest_bundle (bouton)."""
        bundle = _make_bundle()
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            show_crypto_bundles.execute(ctx)
        actions = ctx.embeds_to_emit[0]["bundles"][0]["actions"]
        assert len(actions) == 2
        kinds = {a["kind"] for a in actions}
        assert kinds == {"view_bundle_detail", "invest_bundle"}
        # Les deep-links doivent être whitelistés et résolus.
        for action in actions:
            assert action["deep_link"].startswith("vancelian://app/bundle/")
            assert is_known_deep_link(action["deep_link"])

    def test_returns_allocations_summary_for_llm(self):
        """Le `bundles[*].allocations_summary` doit être présent dans
        la réponse JSON pour que le LLM puisse paraphraser sans
        inventer les pourcentages."""
        bundle = _make_bundle(
            allocations=[
                _make_alloc(asset_symbol="BTC", target_weight="0.50"),
                _make_alloc(
                    asset_symbol="ETH",
                    instrument_name="Ethereum",
                    target_weight="0.20",
                ),
            ]
        )
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            result = show_crypto_bundles.execute(ctx)
        summary = result["bundles"][0]["allocations_summary"]
        assert summary is not None
        assert "50% BTC" in summary
        assert "20% ETH" in summary


# ─────────────────────────────────────────────────────────────────────
# execute() — edge cases
# ─────────────────────────────────────────────────────────────────────


class TestShowCryptoBundlesEdgeCases:
    def test_empty_catalog_returns_no_embed(self):
        """Catalogue vide (aucun bundle public actif en DB) → pas
        d'embed pushé, signal `embed_emitted=False`. Le LLM peut
        ainsi répondre verbalement plutôt que de générer un slider
        vide."""
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[],
        ):
            result = show_crypto_bundles.execute(ctx)
        assert result["bundles_count"] == 0
        assert result["embed_emitted"] is False
        assert result.get("note") == "no_active_bundle"
        assert ctx.embeds_to_emit == []

    def test_catalog_error_returns_error_payload(self):
        """Erreur DB / SQLAlchemy → `{"error": "catalog_unavailable"}`
        sans crash. Le LLM peut alors signaler poliment au client."""
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            side_effect=RuntimeError("simulated DB error"),
        ):
            result = show_crypto_bundles.execute(ctx)
        assert result == {"error": "catalog_unavailable"}
        assert ctx.embeds_to_emit == []

    def test_truncates_to_max_bundles(self):
        """Si > _MAX_BUNDLES bundles en DB, on ne pousse que les 8
        premiers (l'ordre est imposé par CatalogService — tri par
        name)."""
        max_n = show_crypto_bundles._MAX_BUNDLES
        bundles = [
            _make_bundle(name=f"B{i}", product_code=f"B{i}")
            for i in range(max_n + 3)
        ]
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=bundles,
        ):
            result = show_crypto_bundles.execute(ctx)
        assert result["bundles_count"] == max_n
        assert len(ctx.embeds_to_emit[0]["bundles"]) == max_n

    def test_skips_allocation_with_empty_symbol(self):
        """Une alloc sans `asset_symbol` (cas pathologique en DB)
        doit être skippée — pas de crash, pas de leak de None."""
        bundle = _make_bundle(
            allocations=[
                _make_alloc(asset_symbol="BTC", target_weight="0.70"),
                _make_alloc(asset_symbol="", target_weight="0.30"),
            ]
        )
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[bundle],
        ):
            show_crypto_bundles.execute(ctx)
        allocs = ctx.embeds_to_emit[0]["bundles"][0]["allocations"]
        assert len(allocs) == 1
        assert allocs[0]["symbol"] == "BTC"


# ─────────────────────────────────────────────────────────────────────
# execute() — filtrage `product_codes` (Phase 2 wiki v1.4)
# ─────────────────────────────────────────────────────────────────────


class TestShowCryptoBundlesProductCodesFilter:
    def test_filter_keeps_only_matching_codes(self):
        """`product_codes=["TOP_5"]` filtre la liste pour ne garder
        que TOP_5 (case-insensitive)."""
        b1 = _make_bundle(name="Top 2", product_code="TOP_2")
        b2 = _make_bundle(name="Top 5", product_code="TOP_5")
        b3 = _make_bundle(name="Alt 5", product_code="ALT_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[b1, b2, b3],
        ):
            result = show_crypto_bundles.execute(ctx, product_codes=["top_5"])
        assert result["bundles_count"] == 1
        assert result["bundles"][0]["product_code"] == "TOP_5"
        # Embed contient bien la card filtrée.
        assert len(ctx.embeds_to_emit[0]["bundles"]) == 1

    def test_filter_keeps_multiple_matches(self):
        """`product_codes` accepte plusieurs codes — ordre du
        catalogue préservé."""
        b1 = _make_bundle(name="Top 2", product_code="TOP_2")
        b2 = _make_bundle(name="Top 5", product_code="TOP_5")
        b3 = _make_bundle(name="Alt 5", product_code="ALT_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[b1, b2, b3],
        ):
            result = show_crypto_bundles.execute(
                ctx, product_codes=["TOP_5", "ALT_5"]
            )
        assert result["bundles_count"] == 2
        codes = [b["product_code"] for b in result["bundles"]]
        assert codes == ["TOP_5", "ALT_5"]

    def test_filter_no_match_returns_available_codes_hint(self):
        """Aucun code ne matche → le tool retourne les codes
        disponibles pour aider le LLM à proposer une alternative."""
        b1 = _make_bundle(name="Top 2", product_code="TOP_2")
        b2 = _make_bundle(name="Top 5", product_code="TOP_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[b1, b2],
        ):
            result = show_crypto_bundles.execute(
                ctx, product_codes=["BOGUS"]
            )
        assert result["bundles_count"] == 0
        assert result["embed_emitted"] is False
        assert result["note"] == "no_match_for_product_codes"
        assert "TOP_2" in result["available_product_codes"]
        assert "TOP_5" in result["available_product_codes"]
        # Pas d'embed pushé en cas de zéro match.
        assert ctx.embeds_to_emit == []

    def test_filter_empty_list_treated_as_no_filter(self):
        """`product_codes=[]` est équivalent à pas de filtre — tout
        le catalogue est retourné."""
        b1 = _make_bundle(name="Top 2", product_code="TOP_2")
        b2 = _make_bundle(name="Top 5", product_code="TOP_5")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[b1, b2],
        ):
            result = show_crypto_bundles.execute(ctx, product_codes=[])
        assert result["bundles_count"] == 2

    def test_filter_none_treated_as_no_filter(self):
        """`product_codes=None` (défaut) = tout retourner."""
        b1 = _make_bundle(name="Top 2", product_code="TOP_2")
        ctx = _ctx()
        with patch(
            "services.assistance.agents.tools.product.show_crypto_bundles."
            "CatalogService.get_public_catalog",
            return_value=[b1],
        ):
            result = show_crypto_bundles.execute(ctx, product_codes=None)
        assert result["bundles_count"] == 1


# ─────────────────────────────────────────────────────────────────────
# Helper interne `_summarize_allocations`
# ─────────────────────────────────────────────────────────────────────


class TestSummarizeAllocations:
    def test_empty_list_returns_none(self):
        assert show_crypto_bundles._summarize_allocations([]) is None

    def test_zero_weights_returns_none(self):
        """Allocs avec poids nuls → résumé vide → None (le LLM ne doit
        pas afficher ', ' tout seul)."""
        result = show_crypto_bundles._summarize_allocations(
            [{"symbol": "BTC", "weight": 0.0}, {"symbol": "ETH", "weight": 0.0}]
        )
        assert result is None

    def test_truncates_to_top_5(self):
        """On limite à 5 lignes pour rester court côté texte LLM."""
        allocs = [
            {"symbol": f"S{i}", "weight": 0.10} for i in range(10)
        ]
        result = show_crypto_bundles._summarize_allocations(allocs)
        # Compte les virgules pour les 5 premières.
        assert result is not None
        assert result.count(",") == 4

    def test_rounding_pct(self):
        """0.155 → 16% (round half-to-even Python). On vérifie juste
        que c'est un entier sans décimale et > 0."""
        result = show_crypto_bundles._summarize_allocations(
            [{"symbol": "BTC", "weight": 0.155}]
        )
        assert result is not None
        # Format "<int>% BTC"
        assert result.endswith("% BTC")


# ─────────────────────────────────────────────────────────────────────
# action_cta_catalog — nouveaux deep-links
# ─────────────────────────────────────────────────────────────────────


class TestBundleActionsWhitelist:
    def test_view_bundle_detail_known(self):
        assert is_known_kind("view_bundle_detail")
        assert is_available("view_bundle_detail")
        spec = get_spec("view_bundle_detail")
        assert spec is not None
        assert spec.requires_param == "bundle_id"
        assert "{id}" in spec.deep_link_template

    def test_invest_bundle_known(self):
        assert is_known_kind("invest_bundle")
        assert is_available("invest_bundle")
        spec = get_spec("invest_bundle")
        assert spec is not None
        assert spec.requires_param == "bundle_id"
        assert spec.deep_link_template.endswith("/invest")

    def test_build_view_bundle_detail(self):
        action = build_action(
            "view_bundle_detail", params={"bundle_id": "abc-123"}
        )
        assert action is not None
        assert action["kind"] == "view_bundle_detail"
        assert action["deep_link"] == "vancelian://app/bundle/abc-123"
        assert action["label"]  # default_label non vide

    def test_build_invest_bundle(self):
        action = build_action(
            "invest_bundle", params={"bundle_id": "abc-123"}
        )
        assert action is not None
        assert action["kind"] == "invest_bundle"
        assert action["deep_link"] == "vancelian://app/bundle/abc-123/invest"

    def test_build_missing_bundle_id(self):
        """Sans bundle_id → None (le tool ne doit pas embarquer une
        action invalide)."""
        assert build_action("view_bundle_detail", params={}) is None
        assert build_action("invest_bundle", params=None) is None

    @pytest.mark.parametrize(
        "deep_link,expected",
        [
            ("vancelian://app/bundle/abc-123", True),
            ("vancelian://app/bundle/abc-123/invest", True),
            # Manque l'id
            ("vancelian://app/bundle/", False),
            # Sous-chemin non whitelisté
            ("vancelian://app/bundle/abc-123/foo", False),
            # Scheme étranger
            ("https://app/bundle/abc-123", False),
            # Template non résolu
            ("vancelian://app/bundle/{id}", False),
        ],
    )
    def test_is_known_deep_link(self, deep_link: str, expected: bool):
        assert is_known_deep_link(deep_link) is expected


# ─────────────────────────────────────────────────────────────────────
# Guard-rail — show_crypto_bundles est un tool de lecture
# ─────────────────────────────────────────────────────────────────────


class TestShowCryptoBundlesGuardrailIntegration:
    def test_tool_name_in_product_knowledge_read_tools(self):
        """Le guard-rail anti-hallucination du `product` agent doit
        accepter `show_crypto_bundles` comme tool de lecture sourcée
        (équivalent fonctionnel de `show_instrument_card`)."""
        from services.assistance.agents.runtime.agent_loop import (
            PRODUCT_KNOWLEDGE_READ_TOOLS,
        )
        assert "show_crypto_bundles" in PRODUCT_KNOWLEDGE_READ_TOOLS

    def test_guardrail_accepts_show_crypto_bundles_alone(self):
        """Si le LLM produit appelle uniquement show_crypto_bundles
        et répond → pas de retry guard-rail."""
        from services.assistance.agents.runtime.agent_loop import (
            _check_product_guardrail,
        )
        assert _check_product_guardrail(["show_crypto_bundles"]) is None

    def test_guardrail_hint_no_read_mentions_show_crypto_bundles(self):
        """Le hint envoyé au LLM en cas de no-read doit citer
        `show_crypto_bundles` dans la liste des tools acceptables
        (sinon le LLM le voit comme inexistant et risque de ne plus
        l'appeler en retry)."""
        from services.assistance.agents.runtime.agent_loop import (
            PRODUCT_GUARDRAIL_HINT_NO_READ,
        )
        assert "show_crypto_bundles" in PRODUCT_GUARDRAIL_HINT_NO_READ
