"""Tests unitaires Phase 2 wiki v1.4 patch 3 — garde-fou cross-référentiel
sur `read_wiki_page` (slugs SQL `product_basics_*` redirigés).

Cas réel ayant motivé : conv `534d545b` 2026-05-04, l'agent passe 3 slugs
SQL à `read_wiki_page` qui retourne `not_found` → boucles MAX_ITER.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.product import read_wiki_page
from services.assistance.agents.tools.product.read_wiki_page import (
    SQL_KNOWLEDGE_SLUG_PREFIXES,
    SQL_KNOWLEDGE_SLUGS_EXACT,
    _is_sql_knowledge_slug,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx() -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=str(uuid4()),
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="product",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t",
    )


# ─────────────────────────────────────────────────────────────────────
# A. Détection d'un slug SQL
# ─────────────────────────────────────────────────────────────────────


class TestIsSqlKnowledgeSlug:
    @pytest.mark.parametrize(
        "slug",
        [
            "product_basics_vault",
            "product_basics_exclusive_offer",
            "product_basics_crypto_bundle",
            "product_basics_livret_vancelian",
            "product_basics_scpi",
            "deposit_delay_sepa_in",
            "deposit_delay_card",
            "deposit_delay_crypto_in",
            "withdrawal_delay_sepa_out",
            "withdrawal_delay_crypto_out",
            "kyc_review_typical_delay",
            "swap_settlement_immediate",
            "kind_subscribe_vault",
            "vancelian_product_catalog",
        ],
    )
    def test_known_sql_slugs_detected(self, slug):
        assert _is_sql_knowledge_slug(slug) is True

    @pytest.mark.parametrize(
        "slug",
        [
            "how-do-i-create-a-flexible-vault",
            "what-is-the-7-luxury-villas-in-bali-exclusive-offer",
            "cloud-mining-yield-factors",
            "the-trading-fees",
            "vancelian-cryptocurrencies-overview",
            # Pas de tiret bas → pas un slug SQL.
            "vault-vs-exclusive-offer",
        ],
    )
    def test_wiki_md_slugs_not_detected(self, slug):
        assert _is_sql_knowledge_slug(slug) is False

    def test_empty_slug_not_detected(self):
        assert _is_sql_knowledge_slug("") is False
        assert _is_sql_knowledge_slug(None) is False  # type: ignore[arg-type]

    def test_case_insensitive(self):
        assert _is_sql_knowledge_slug("PRODUCT_BASICS_VAULT") is True
        assert _is_sql_knowledge_slug("Vancelian_Product_Catalog") is True

    def test_perimeter_documented(self):
        """Sanity check : la liste des préfixes est cohérente avec les
        seeds DB connus (149 + 151)."""
        for prefix in (
            "product_basics_",
            "deposit_delay_",
            "withdrawal_delay_",
            "kyc_",
            "swap_",
            "kind_",
        ):
            assert prefix in SQL_KNOWLEDGE_SLUG_PREFIXES
        assert "vancelian_product_catalog" in SQL_KNOWLEDGE_SLUGS_EXACT


# ─────────────────────────────────────────────────────────────────────
# B. read_wiki_page.execute — garde-fou actif
# ─────────────────────────────────────────────────────────────────────


class TestReadWikiPageGuard:
    def test_sql_slug_returns_wrong_repo_with_hint(self):
        out = read_wiki_page.execute(
            _ctx(),
            category="exclusive-offers",
            slug="product_basics_exclusive_offer",
        )
        assert out["error"] == "wrong_repo"
        assert out["use_tool"] == "read_product_knowledge"
        assert "product_basics_exclusive_offer" in out["hint"]
        assert "read_product_knowledge" in out["hint"]

    def test_sql_slug_with_any_category_redirected(self):
        """Le préfixe SQL doit primer sur la catégorie : peu importe
        ce que le LLM met en `category`, on redirige."""
        for cat in ("savings", "exclusive-offers", "crypto", "definition"):
            out = read_wiki_page.execute(
                _ctx(),
                category=cat,
                slug="product_basics_vault",
            )
            assert out["error"] == "wrong_repo", f"failed for category={cat}"

    def test_catalog_slug_redirected_too(self):
        out = read_wiki_page.execute(
            _ctx(),
            category="savings",
            slug="vancelian_product_catalog",
        )
        assert out["error"] == "wrong_repo"
        assert "vancelian_product_catalog" in out["hint"]

    def test_normal_wiki_slug_not_blocked(self):
        """Slug légitime du wiki MD (kebab-case) : pas de redirection.
        On ne teste PAS le succès du fetch (dépend du wiki présent),
        juste qu'on n'a pas le code `wrong_repo`."""
        out = read_wiki_page.execute(
            _ctx(),
            category="savings",
            slug="how-do-i-create-a-flexible-vault",
        )
        assert out.get("error") != "wrong_repo"

    def test_missing_slug_still_returns_missing_args(self):
        out = read_wiki_page.execute(_ctx(), category="savings", slug="")
        assert out["error"] == "missing_args"

    def test_unknown_category_still_returns_unknown_category(self):
        """Le garde-fou SQL ne doit pas déclencher sur slug wiki normal
        avec catégorie invalide (= ancien code path préservé)."""
        out = read_wiki_page.execute(
            _ctx(),
            category="totally-fake-category",
            slug="how-do-i-create-a-flexible-vault",
        )
        # Soit unknown_category, soit not_found — pas wrong_repo.
        assert out["error"] in ("unknown_category", "not_found")
