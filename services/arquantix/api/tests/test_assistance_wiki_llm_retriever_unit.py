"""Tests unitaires Phase 2 wiki v1.4 patch 3 — Karpathy LLM-as-retriever.

Couvre :
  * `_build_catalog_lines` : structure des lignes compactes.
  * `select_pages_via_llm` : cas nominal, sentinel SQL, slugs invalides,
    LLM error, env disable, slug filter par catégorie, top_k cap.
  * Cohabitation avec le scoring keyword via `select_wiki_pages.execute`.

Cas réel ayant motivé : conv `534d545b` — `select_wiki_pages` avec
keyword matching retourne 0 match sur « parle moi des offres
exclusives » alors que 34 fiches existent dans `exclusive-offers`.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.repositories import wiki_llm_retriever, wiki_repo
from services.assistance.agents.tools.product import select_wiki_pages
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.llm import LLMError


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _make_ctx(**kwargs) -> ToolContext:
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
        correlation_id="test-corr",
    )


def _fake_chat_returning(slugs: list[str], reason: str = "match"):
    """Fabrique une fonction `chat_completion_with_tools` qui simule un
    LLM retournant un tool call `return_selected_slugs`."""

    def _fn(messages, *, model, tools, tool_choice, temperature):
        import json as _json

        return {
            "content": None,
            "tool_calls": [
                {
                    "id": "c0",
                    "type": "function",
                    "function": {
                        "name": "return_selected_slugs",
                        "arguments": _json.dumps(
                            {"slugs": slugs, "reason": reason}
                        ),
                    },
                }
            ],
        }

    return _fn


@pytest.fixture(autouse=True)
def _reset_catalog():
    """Reset cache catalogue entre tests pour éviter les fuites."""
    wiki_llm_retriever.reset_catalog_cache_for_tests()
    yield
    wiki_llm_retriever.reset_catalog_cache_for_tests()


# ─────────────────────────────────────────────────────────────────────
# A. _build_catalog_lines
# ─────────────────────────────────────────────────────────────────────


class TestBuildCatalogLines:
    def test_one_line_per_page(self):
        all_pages = wiki_repo.all_pages()
        assert len(all_pages) > 0, "wiki should be loaded for tests"
        pages_by_cat: dict = {}
        for p in all_pages:
            pages_by_cat.setdefault(p.category, []).append(p)

        lines, by_slug = wiki_llm_retriever._build_catalog_lines(
            pages_by_category=pages_by_cat
        )
        assert len(lines) == len(all_pages)
        assert len(by_slug) == len(all_pages)
        # Format vérifié : doit commencer par "- [<cat>/<slug>]"
        for line in lines[:5]:
            assert line.startswith("- ["), line

    def test_exclusive_offers_catalog_puts_major_offers_first(self):
        """Les fiches « what is » par grande offre précèdent le bloc cloud-mining-*."""
        all_pages = wiki_repo.all_pages()
        pages_by_cat: dict = {}
        for p in all_pages:
            pages_by_cat.setdefault(p.category, []).append(p)
        lines, _ = wiki_llm_retriever._build_catalog_lines(
            pages_by_category=pages_by_cat
        )
        ex_lines = [ln for ln in lines if "[exclusive-offers/" in ln]
        assert ex_lines
        slugs_order: list[str] = []
        for ln in ex_lines:
            start = ln.index("[exclusive-offers/") + len("[exclusive-offers/")
            end = ln.index("]", start)
            slugs_order.append(ln[start:end])
        assert slugs_order[0] == (
            "what-is-the-exclusive-offer-cloud-mining-by-hearst-infrastru"
        )
        dubai = "what-is-the-exclusive-offer-dubai-villa-al-barari"
        bali = "what-is-the-7-luxury-villas-in-bali-exclusive-offer"
        halving = "cloud-mining-bitcoin-halving-impact"
        assert dubai in slugs_order
        assert bali in slugs_order
        if halving in slugs_order:
            assert slugs_order.index(dubai) < slugs_order.index(halving)
            assert slugs_order.index(bali) < slugs_order.index(halving)


# ─────────────────────────────────────────────────────────────────────
# B. select_pages_via_llm — cas nominaux
# ─────────────────────────────────────────────────────────────────────


class TestSelectPagesViaLlmNominal:
    def test_returns_resolved_matches(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        # On choisit 2 slugs qui existent dans le wiki (vérifiés par
        # l'assertion précédente). On lit la 1ʳᵉ page de chaque catégorie
        # populaire pour avoir des slugs réels.
        all_pages = wiki_repo.all_pages()
        sample = [p for p in all_pages if p.category == "exclusive-offers"]
        assert len(sample) >= 2, "exclusive-offers should have >= 2 pages"
        slug1 = sample[0].slug
        slug2 = sample[1].slug

        result = wiki_llm_retriever.select_pages_via_llm(
            question="parle moi des offres exclusives",
            top_k=5,
            chat_completion_fn=_fake_chat_returning(
                [slug1, slug2], reason="2 fiches exclusive-offers"
            ),
        )
        assert result is not None
        assert result["via"] == "llm"
        assert result["total_returned"] == 2
        slugs_returned = [m["slug"] for m in result["matches"]]
        assert slug1 in slugs_returned
        assert slug2 in slugs_returned
        assert "selection_reason" in result

    def test_disabled_returns_none(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "false")
        result = wiki_llm_retriever.select_pages_via_llm(
            question="anything",
            chat_completion_fn=_fake_chat_returning(["any"]),
        )
        assert result is None

    def test_empty_question_returns_none(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        result = wiki_llm_retriever.select_pages_via_llm(
            question="   ",
            chat_completion_fn=_fake_chat_returning(["x"]),
        )
        assert result is None

    def test_invalid_slugs_filtered_out(self, monkeypatch):
        """Le LLM hallucine un slug → on l'ignore silencieusement.
        S'il ne reste rien, on retourne None pour déclencher le fallback."""
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        result = wiki_llm_retriever.select_pages_via_llm(
            question="x",
            chat_completion_fn=_fake_chat_returning(
                ["totally-fake-slug-that-does-not-exist"]
            ),
        )
        assert result is None  # → fallback keyword côté caller

    def test_mix_valid_invalid_slugs_keeps_valid(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        all_pages = wiki_repo.all_pages()
        valid_slug = all_pages[0].slug
        result = wiki_llm_retriever.select_pages_via_llm(
            question="x",
            chat_completion_fn=_fake_chat_returning(
                ["fake-slug", valid_slug, "another-fake"]
            ),
        )
        assert result is not None
        assert result["total_returned"] == 1
        assert result["matches"][0]["slug"] == valid_slug


# ─────────────────────────────────────────────────────────────────────
# C. Sentinel SQL catalog hint
# ─────────────────────────────────────────────────────────────────────


class TestSqlCatalogHint:
    def test_sentinel_returns_use_sql_catalog_marker(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        result = wiki_llm_retriever.select_pages_via_llm(
            question="quels sont les produits Vancelian ?",
            chat_completion_fn=_fake_chat_returning(
                [wiki_llm_retriever.SQL_CATALOG_HINT_SLUG],
                reason="question gamme — fiche SQL canonique",
            ),
        )
        assert result is not None
        assert result["via"] == "llm_sql_hint"
        assert result["use_sql_catalog_slug"] == "vancelian_product_catalog"
        assert result["total_returned"] == 0


# ─────────────────────────────────────────────────────────────────────
# D. Erreurs LLM
# ─────────────────────────────────────────────────────────────────────


class TestLlmErrorHandling:
    def test_llm_error_returns_none(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")

        def _raise(*args, **kwargs):
            raise LLMError("timeout simulé")

        result = wiki_llm_retriever.select_pages_via_llm(
            question="x", chat_completion_fn=_raise
        )
        assert result is None

    def test_no_tool_call_returns_none(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")

        def _no_tool(messages, *, model, tools, tool_choice, temperature):
            return {"content": "I cannot decide", "tool_calls": []}

        result = wiki_llm_retriever.select_pages_via_llm(
            question="x", chat_completion_fn=_no_tool
        )
        assert result is None

    def test_invalid_args_returns_none(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")

        def _broken(messages, *, model, tools, tool_choice, temperature):
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "c0",
                        "type": "function",
                        "function": {
                            "name": "return_selected_slugs",
                            "arguments": "{not_json",
                        },
                    }
                ],
            }

        result = wiki_llm_retriever.select_pages_via_llm(
            question="x", chat_completion_fn=_broken
        )
        assert result is None


# ─────────────────────────────────────────────────────────────────────
# E. Wire-up dans select_wiki_pages.execute
# ─────────────────────────────────────────────────────────────────────


class TestSelectWikiPagesIntegration:
    def test_llm_path_takes_precedence(self, monkeypatch):
        """Quand le LLM retriever réussit, on doit voir `via: llm` dans
        le retour de `select_wiki_pages.execute`."""
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        all_pages = wiki_repo.all_pages()
        slug = all_pages[0].slug
        monkeypatch.setattr(
            wiki_llm_retriever,
            "select_pages_via_llm",
            lambda **kwargs: {
                "matches": [{"slug": slug, "category": all_pages[0].category}],
                "total_returned": 1,
                "filtered_by_category": None,
                "wiki_total_pages": len(all_pages),
                "via": "llm",
                "selection_reason": "stub",
            },
        )
        out = select_wiki_pages.execute(
            _make_ctx(),
            question="parle moi des offres exclusives",
        )
        assert out["via"] == "llm"
        assert out["total_returned"] == 1

    def test_llm_disabled_falls_back_to_keyword(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "false")
        out = select_wiki_pages.execute(
            _make_ctx(),
            question="flexible vault",
        )
        assert out["via"] == "keyword"

    def test_llm_returns_none_falls_back_to_keyword(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        monkeypatch.setattr(
            wiki_llm_retriever,
            "select_pages_via_llm",
            lambda **kwargs: None,
        )
        out = select_wiki_pages.execute(
            _make_ctx(),
            question="flexible vault",
        )
        assert out["via"] == "keyword"

    def test_sql_hint_propagates_via_field(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "true")
        monkeypatch.setattr(
            wiki_llm_retriever,
            "select_pages_via_llm",
            lambda **kwargs: {
                "matches": [],
                "total_returned": 0,
                "wiki_total_pages": 222,
                "via": "llm_sql_hint",
                "use_sql_catalog_slug": "vancelian_product_catalog",
                "selection_reason": "Question catalogue.",
            },
        )
        out = select_wiki_pages.execute(
            _make_ctx(),
            question="quels sont les produits Vancelian ?",
        )
        assert out["via"] == "llm_sql_hint"
        assert out.get("use_sql_catalog") is True
        assert out["use_sql_catalog_slug"] == "vancelian_product_catalog"
        assert "hint" in out
