"""Tests unitaires Phase 2 wiki — repo + tools + registry.

Couvre :
  * `wiki_repo`
      - parse frontmatter (scalaires, listes inline, listes multi-lignes)
      - extract section markdown (Short answer, Details)
      - cache TTL + invalidate
      - tokenisation + scoring keyword
      - select_pages (top_k, filtre catégorie, seuil min_score)
      - fetch_page (catégorie inconnue, slug introuvable, succès)
      - list_pages
  * tool `select_wiki_pages`
      - question vide / blanche → matches: []
      - catégorie inconnue → error: unknown_category
      - top_k cap à 10
      - succès : payload conforme
  * tool `read_wiki_page`
      - missing args → error: missing_args
      - catégorie inconnue → error: unknown_category
      - not_found
      - succès : payload conforme
  * registry : `product` agent expose les 2 nouveaux tools

Spec : `docs/arquantix/PRODUCT_AGENT.md` §9.1 + §11.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.repositories import wiki_repo
from services.assistance.agents.tools import registry as tools_registry
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.product import (
    read_wiki_page,
    select_wiki_pages,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx() -> ToolContext:
    """ToolContext minimal pour un agent product. DB pas utilisée par
    les tools wiki (lecture filesystem pure)."""
    return ToolContext(
        db=MagicMock(),
        client_id=None,
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="product",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-wiki",
    )


# Fixture page partagée pour la majorité des tests — évite de hammerer
# le filesystem à chaque test (le cache RAM s'en charge déjà mais on
# précharge en début de session).
@pytest.fixture(scope="module", autouse=True)
def _reset_wiki_cache_once():
    """Force un reload propre du cache au début du module pour avoir
    une vue stable du wiki sur disque."""
    wiki_repo.invalidate_cache()
    yield
    wiki_repo.invalidate_cache()


# ─────────────────────────────────────────────────────────────────
# wiki_repo : parsing frontmatter + sections
# ─────────────────────────────────────────────────────────────────


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_dict(self):
        fm, body = wiki_repo._parse_frontmatter("# Just a title\nbody")
        assert fm == {}
        assert body == "# Just a title\nbody"

    def test_scalar_fields(self):
        text = "---\ntitle: Hello world\nstatus: verified\n---\n\nbody\n"
        fm, body = wiki_repo._parse_frontmatter(text)
        assert fm["title"] == "Hello world"
        assert fm["status"] == "verified"
        assert "body" in body

    def test_quoted_scalar(self):
        text = '---\ntitle: "Quoted: with colon"\n---\n\nbody'
        fm, _ = wiki_repo._parse_frontmatter(text)
        assert fm["title"] == "Quoted: with colon"

    def test_inline_list(self):
        text = "---\ntags: [a, b, c]\n---\n\nbody"
        fm, _ = wiki_repo._parse_frontmatter(text)
        assert fm["tags"] == ["a", "b", "c"]

    def test_multiline_list(self):
        text = (
            "---\n"
            "questions:\n"
            "  - first\n"
            "  - second phrasing\n"
            "  - third\n"
            "title: After list\n"
            "---\n\n"
            "body"
        )
        fm, _ = wiki_repo._parse_frontmatter(text)
        assert fm["questions"] == ["first", "second phrasing", "third"]
        assert fm["title"] == "After list"

    def test_malformed_frontmatter_no_close(self):
        text = "---\ntitle: missing close\nno end here\n"
        fm, body = wiki_repo._parse_frontmatter(text)
        assert fm == {}
        assert body == text


class TestExtractSection:
    def test_section_found(self):
        body = (
            "# Title\n\n"
            "## Short answer\n"
            "Direct sentence.\n\n"
            "## Details\n"
            "Long content.\n"
        )
        out = wiki_repo._extract_section(body, "Short answer")
        assert out == "Direct sentence."

    def test_section_case_insensitive(self):
        body = "## SHORT answer\nFoo\n## Details\nBar"
        assert wiki_repo._extract_section(body, "short answer") == "Foo"

    def test_section_not_found(self):
        body = "## Details\nOnly details here"
        assert wiki_repo._extract_section(body, "Short answer") is None

    def test_empty_body(self):
        assert wiki_repo._extract_section("", "Short answer") is None
        assert wiki_repo._extract_section("body", "") is None


class TestTokenize:
    def test_strips_stopwords_and_short_tokens(self):
        tokens = wiki_repo._tokenize("Comment fonctionne le Coffre Avenir ?")
        # "comment", "le" → stopwords. "?" stripped. "le"<3 ?
        # In our stoplist, "le" is included → filtered. So we should keep
        # "comment" only if not in stoplist. Per our stoplist, "comment"
        # IS a stopword. → tokens = ["fonctionne", "coffre", "avenir"]
        assert "fonctionne" in tokens
        assert "coffre" in tokens
        assert "avenir" in tokens
        assert "le" not in tokens
        assert "comment" not in tokens

    def test_lowercase(self):
        tokens = wiki_repo._tokenize("BITCOIN halving 2024")
        assert "bitcoin" in tokens
        assert "halving" in tokens
        assert "2024" in tokens

    def test_empty(self):
        assert wiki_repo._tokenize("") == []
        assert wiki_repo._tokenize(None) == []  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────
# wiki_repo : scoring + select_pages (mocked pages)
# ─────────────────────────────────────────────────────────────────


def _mk_page(
    *,
    category="savings",
    slug="my-page",
    title="My Page Title",
    status="verified",
    audience="client",
    questions=(),
    tags=(),
    short_answer=None,
    details=None,
):
    return wiki_repo.WikiPage(
        category=category,
        slug=slug,
        title=title,
        status=status,
        audience=audience,
        last_reviewed="2026-04-12",
        questions=questions,
        sources=(),
        related=(),
        tags=tags,
        short_answer=short_answer,
        details=details,
        body_markdown="",
    )


class TestScorePage:
    def test_match_in_questions_scores_high(self):
        page = _mk_page(
            questions=("how does the flexible vault work",),
            title="Flexible Vault explained",
        )
        score, matched = wiki_repo._score_page(
            page, {"flexible", "vault"}
        )
        # 2 tokens dans questions (×1.0) + 2 dans title (×0.5) = 3.0,
        # ×1.2 (verified) = 3.6
        assert score == pytest.approx(3.6, rel=0.01)
        assert "flexible" in matched
        assert "vault" in matched

    def test_no_match_returns_zero(self):
        page = _mk_page(
            questions=("how does the flexible vault work",),
            title="Flexible Vault",
        )
        score, matched = wiki_repo._score_page(page, {"unrelated", "tokens"})
        assert score == 0.0
        assert matched == []

    def test_stale_status_penalty(self):
        page = _mk_page(
            status="stale",
            questions=("test page",),
            title="Test Page",
        )
        score, _ = wiki_repo._score_page(page, {"test"})
        # 1 in questions + 0.5 in title = 1.5 ; × 0.5 (stale) = 0.75
        assert score == pytest.approx(0.75, rel=0.01)

    def test_empty_question_tokens(self):
        page = _mk_page(questions=("test",))
        score, matched = wiki_repo._score_page(page, set())
        assert score == 0.0
        assert matched == []


class TestSelectPages:
    def test_empty_question_returns_empty(self):
        assert wiki_repo.select_pages(question="") == []
        assert wiki_repo.select_pages(question="   ") == []

    def test_top_k_clamped_to_10(self):
        # On utilise le wiki réel (243 pages). Top_k > 10 doit clamper.
        out = wiki_repo.select_pages(
            question="vault crypto exchange", top_k=999
        )
        assert len(out) <= 10

    def test_top_k_clamped_to_min_1(self):
        out = wiki_repo.select_pages(question="vault", top_k=0)
        # 0 → clampé à 1
        assert len(out) <= 1

    def test_filter_category(self):
        # Filtre savings : aucune fiche d'autres catégories ne doit
        # apparaître.
        out = wiki_repo.select_pages(
            question="vault", top_k=10, category="savings"
        )
        for page, _, _ in out:
            assert page.category == "savings"

    def test_unknown_category_returns_empty(self):
        out = wiki_repo.select_pages(
            question="vault", top_k=5, category="not_a_real_cat"
        )
        assert out == []


class TestFetchPage:
    def test_empty_args(self):
        assert wiki_repo.fetch_page(category="", slug="x") is None
        assert wiki_repo.fetch_page(category="savings", slug="") is None

    def test_unknown_category(self):
        assert wiki_repo.fetch_page(category="notacat", slug="x") is None

    def test_not_in_cache_returns_none(self):
        out = wiki_repo.fetch_page(
            category="savings", slug="this-slug-does-not-exist-1234"
        )
        assert out is None


class TestListPages:
    def test_returns_minimal_fields(self):
        out = wiki_repo.list_pages(category="savings", limit=3)
        for entry in out:
            assert set(entry.keys()) == {
                "category",
                "slug",
                "title",
                "status",
            }
            assert entry["category"] == "savings"

    def test_limit_clamped(self):
        out = wiki_repo.list_pages(limit=5)
        assert len(out) <= 5


# ─────────────────────────────────────────────────────────────────
# Tool select_wiki_pages
# ─────────────────────────────────────────────────────────────────


class TestSelectWikiPagesTool:
    def test_spec_is_l0_product(self):
        assert select_wiki_pages.SPEC["autonomy_level"] == "L0"
        assert select_wiki_pages.SPEC["agent_id"] == "product"
        assert (
            select_wiki_pages.SPEC["function"]["name"]
            == "select_wiki_pages"
        )

    def test_empty_question(self):
        result = select_wiki_pages.execute(_ctx(), question="")
        assert result["matches"] == []
        assert result["total_returned"] == 0

    def test_unknown_category(self):
        result = select_wiki_pages.execute(
            _ctx(), question="something", category="not_a_cat"
        )
        assert result.get("error") == "unknown_category"
        assert result["matches"] == []

    def test_repo_error_returns_empty(self, monkeypatch):
        # Phase 2 wiki v1.4 patch 3 — désactive le LLM retriever pour
        # tester le fallback keyword scoring legacy.
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "false")
        with patch.object(
            select_wiki_pages.wiki_repo,
            "select_pages",
            side_effect=RuntimeError("boom"),
        ):
            result = select_wiki_pages.execute(
                _ctx(), question="anything"
            )
        assert result.get("error") == "repo_error"
        assert result["matches"] == []

    def test_success_payload_shape(self, monkeypatch):
        # Phase 2 wiki v1.4 patch 3 — désactive le LLM retriever pour
        # tester directement le format du payload côté keyword path.
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "false")
        page = _mk_page(
            category="savings",
            slug="what-is-the-flexible-vault",
            title="What is the Flexible Vault?",
            questions=("what is the flexible vault",),
            tags=("vault", "flexible"),
        )
        with patch.object(
            select_wiki_pages.wiki_repo,
            "select_pages",
            return_value=[(page, 4.2, ["flexible", "vault"])],
        ):
            result = select_wiki_pages.execute(
                _ctx(),
                question="what is the flexible vault",
                top_k=3,
            )
        assert result["total_returned"] == 1
        assert len(result["matches"]) == 1
        match = result["matches"][0]
        assert match["category"] == "savings"
        assert match["slug"] == "what-is-the-flexible-vault"
        assert match["title"] == "What is the Flexible Vault?"
        assert match["score"] == 4.2
        assert match["matched_terms"] == ["flexible", "vault"]
        assert "what is the flexible vault" in match[
            "matched_questions_preview"
        ]


# ─────────────────────────────────────────────────────────────────
# Tool read_wiki_page
# ─────────────────────────────────────────────────────────────────


class TestReadWikiPageTool:
    def test_spec_is_l0_product(self):
        assert read_wiki_page.SPEC["autonomy_level"] == "L0"
        assert read_wiki_page.SPEC["agent_id"] == "product"
        assert (
            read_wiki_page.SPEC["function"]["name"] == "read_wiki_page"
        )

    def test_missing_args(self):
        assert (
            read_wiki_page.execute(_ctx(), category="", slug="x")[
                "error"
            ]
            == "missing_args"
        )
        assert (
            read_wiki_page.execute(_ctx(), category="savings", slug="")[
                "error"
            ]
            == "missing_args"
        )

    def test_unknown_category(self):
        result = read_wiki_page.execute(
            _ctx(), category="notacat", slug="x"
        )
        assert result["error"] == "unknown_category"

    def test_not_found(self):
        with patch.object(
            read_wiki_page.wiki_repo, "fetch_page", return_value=None
        ):
            result = read_wiki_page.execute(
                _ctx(), category="savings", slug="nope"
            )
        assert result["error"] == "not_found"
        assert result["category"] == "savings"
        assert result["slug"] == "nope"

    def test_repo_error(self):
        with patch.object(
            read_wiki_page.wiki_repo,
            "fetch_page",
            side_effect=RuntimeError("boom"),
        ):
            result = read_wiki_page.execute(
                _ctx(), category="savings", slug="any"
            )
        assert result["error"] == "repo_error"

    def test_success_returns_payload(self):
        page = _mk_page(
            category="savings",
            slug="what-is-the-flexible-vault",
            title="Flexible Vault",
            short_answer="Direct answer.",
            details="Long content.",
            questions=("what is the flexible vault",),
            tags=("vault",),
        )
        with patch.object(
            read_wiki_page.wiki_repo, "fetch_page", return_value=page
        ):
            result = read_wiki_page.execute(
                _ctx(),
                category="SAVINGS",  # case-insensitive on category
                slug="what-is-the-flexible-vault",
            )
        assert result.get("error") is None
        assert result["title"] == "Flexible Vault"
        assert result["short_answer"] == "Direct answer."
        assert result["details"] == "Long content."
        assert result["questions"] == ["what is the flexible vault"]


# ─────────────────────────────────────────────────────────────────
# Registry wiring
# ─────────────────────────────────────────────────────────────────


class TestRegistryWiring:
    def test_product_has_wiki_tools(self):
        names = tools_registry.all_tool_names("product")
        assert "select_wiki_pages" in names
        assert "read_wiki_page" in names
        # Phase 2c — tools SQL product_knowledge volontairement absents (désactivés).
        assert "read_product_knowledge" not in names
        assert "list_product_knowledge_topics" not in names
        assert "show_instrument_card" in names
        # Phase 2 wiki — slider crypto_bundles_card
        assert "show_crypto_bundles" in names
        assert "ask_user_question" in names
        # Garde-fous structurels (anti-récursion product)
        assert "consult_specialist" not in names
        assert "handoff_to_agent" not in names

    def test_product_total_tool_count(self):
        names = tools_registry.all_tool_names("product")
        # 6 tools : wiki×2 + instrument + bundles + bundle detail + ask
        assert len(names) == 6

    def test_compliance_top_level_does_NOT_get_wiki_tools(self):
        """L'agent `compliance` top-level (entry-point dispatcher) au
        tour 0 n'a accès qu'à `diagnose_compliance_topic` +
        `ask_user_question`. Le wiki n'arrive qu'après dispatch sur
        un sub-agent `compliance.<topic>`."""
        names = tools_registry.all_tool_names("compliance")
        assert "select_wiki_pages" not in names
        assert "read_wiki_page" not in names

    def test_default_agent_does_NOT_get_wiki_tools(self):
        """L'agent `default` (fallback) reste minimal."""
        names = tools_registry.all_tool_names("default")
        assert "select_wiki_pages" not in names
        assert "read_wiki_page" not in names

    def test_show_crypto_bundles_stays_product_only(self):
        """`show_crypto_bundles` reste strictement réservé à l'agent
        `product` (cf. ToolSpec) — Lot 1 « Wiki shared » ne touche
        pas aux widgets produit."""
        for agent_id in (
            "compliance",
            "compliance.registration",
            "compliance.remediation",
            "compliance.transactional",
            "compliance.general",
            "advisor",
            "market",
            "default",
        ):
            names = tools_registry.all_tool_names(agent_id)
            assert "show_crypto_bundles" not in names, (
                f"{agent_id} ne doit PAS exposer show_crypto_bundles "
                "(réservé au specialist product)."
            )

    def test_find_dispatches_to_module(self):
        mod = tools_registry.find("product", "select_wiki_pages")
        assert mod is select_wiki_pages
        mod = tools_registry.find("product", "read_wiki_page")
        assert mod is read_wiki_page


# ─────────────────────────────────────────────────────────────────
# Lot 1 « Wiki shared » (2026-05-06) — registry cross-agent
# ─────────────────────────────────────────────────────────────────


class TestRegistrySharedWikiLot1:
    """Wiki exposé à tous les sub-agents (compliance.*, advisor, market)."""

    @pytest.mark.parametrize(
        "agent_id",
        [
            "compliance.registration",
            "compliance.remediation",
            "compliance.transactional",
            "compliance.general",
            "advisor",
            "market",
            "trust",  # déjà historique — sanity check
            "product",  # déjà historique — sanity check
        ],
    )
    def test_agent_exposes_select_wiki_pages(self, agent_id):
        names = tools_registry.all_tool_names(agent_id)
        assert "select_wiki_pages" in names, (
            f"{agent_id} doit exposer select_wiki_pages (Lot 1)."
        )

    @pytest.mark.parametrize(
        "agent_id",
        [
            "compliance.registration",
            "compliance.remediation",
            "compliance.transactional",
            "compliance.general",
            "advisor",
            "market",
            "trust",
            "product",
        ],
    )
    def test_agent_exposes_read_wiki_page(self, agent_id):
        names = tools_registry.all_tool_names(agent_id)
        assert "read_wiki_page" in names, (
            f"{agent_id} doit exposer read_wiki_page (Lot 1)."
        )

    def test_find_resolves_wiki_tools_for_compliance_subagent(self):
        """Le dispatcher runtime doit résoudre les tools wiki pour
        un sub-agent compliance (sinon le LLM verra `tool_not_found`)."""
        mod = tools_registry.find(
            "compliance.transactional", "select_wiki_pages"
        )
        assert mod is select_wiki_pages
        mod = tools_registry.find(
            "compliance.transactional", "read_wiki_page"
        )
        assert mod is read_wiki_page


# ─────────────────────────────────────────────────────────────────
# Lot 1 « Wiki shared » (2026-05-06) — garde-fou audience cross-agent
# ─────────────────────────────────────────────────────────────────


def _ctx_for_agent(agent_id: str) -> ToolContext:
    """ToolContext pour un agent donné — utilisé par les tests
    audience guard."""
    return ToolContext(
        db=MagicMock(),
        client_id=None,
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id=agent_id,
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-audience",
    )


class TestSelectWikiPagesAudienceGuard:
    """Filtre `audience: internal` pour les agents non-product."""

    def test_select_filters_internal_for_compliance_transactional(
        self, monkeypatch
    ):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "false")
        client_page = _mk_page(
            category="savings",
            slug="public-faq",
            title="Public FAQ",
            audience="client",
            questions=("test",),
        )
        internal_page = _mk_page(
            category="savings",
            slug="internal-note",
            title="Internal Note",
            audience="internal",
            questions=("test",),
        )
        with patch.object(
            select_wiki_pages.wiki_repo,
            "select_pages",
            return_value=[
                (client_page, 4.0, ["test"]),
                (internal_page, 3.5, ["test"]),
            ],
        ):
            result = select_wiki_pages.execute(
                _ctx_for_agent("compliance.transactional"),
                question="test",
            )
        slugs = [m["slug"] for m in result["matches"]]
        assert "public-faq" in slugs
        assert "internal-note" not in slugs
        assert result["audience_filtered_out"] == 1

    def test_select_keeps_internal_for_product_agent(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "false")
        client_page = _mk_page(
            category="savings",
            slug="public-faq",
            title="Public FAQ",
            audience="client",
            questions=("test",),
        )
        internal_page = _mk_page(
            category="savings",
            slug="internal-note",
            title="Internal Note",
            audience="internal",
            questions=("test",),
        )
        with patch.object(
            select_wiki_pages.wiki_repo,
            "select_pages",
            return_value=[
                (client_page, 4.0, ["test"]),
                (internal_page, 3.5, ["test"]),
            ],
        ):
            result = select_wiki_pages.execute(
                _ctx_for_agent("product"),
                question="test",
            )
        slugs = [m["slug"] for m in result["matches"]]
        assert "public-faq" in slugs
        assert "internal-note" in slugs
        assert result["audience_filtered_out"] == 0

    def test_select_dict_payload_includes_audience_field(self, monkeypatch):
        """Régression : `to_select_dict` doit inclure `audience` pour
        permettre le filtrage cross-agent."""
        monkeypatch.setenv("ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED", "false")
        page = _mk_page(
            category="savings",
            slug="any",
            title="Any",
            audience="client",
            questions=("x",),
        )
        with patch.object(
            select_wiki_pages.wiki_repo,
            "select_pages",
            return_value=[(page, 1.0, ["x"])],
        ):
            result = select_wiki_pages.execute(
                _ctx_for_agent("product"), question="x"
            )
        assert result["matches"][0]["audience"] == "client"


class TestReadWikiPageAudienceGuard:
    """Blocage des fiches `audience: internal` pour les non-product."""

    def test_read_blocks_internal_for_compliance_transactional(self):
        page = _mk_page(
            category="savings",
            slug="internal-note",
            audience="internal",
            short_answer="hidden",
            details="hidden details",
        )
        with patch.object(
            read_wiki_page.wiki_repo, "fetch_page", return_value=page
        ):
            result = read_wiki_page.execute(
                _ctx_for_agent("compliance.transactional"),
                category="savings",
                slug="internal-note",
            )
        assert result["error"] == "audience_restricted"
        assert result["audience"] == "internal"
        assert "hint" in result
        assert "short_answer" not in result
        assert "details" not in result

    def test_read_blocks_internal_for_advisor(self):
        page = _mk_page(audience="internal")
        with patch.object(
            read_wiki_page.wiki_repo, "fetch_page", return_value=page
        ):
            result = read_wiki_page.execute(
                _ctx_for_agent("advisor"),
                category="savings",
                slug="any",
            )
        assert result["error"] == "audience_restricted"

    def test_read_allows_internal_for_product(self):
        page = _mk_page(
            audience="internal",
            short_answer="ok",
            details="ok details",
        )
        with patch.object(
            read_wiki_page.wiki_repo, "fetch_page", return_value=page
        ):
            result = read_wiki_page.execute(
                _ctx_for_agent("product"),
                category="savings",
                slug="any",
            )
        assert result.get("error") is None
        assert result["short_answer"] == "ok"

    def test_read_allows_client_audience_for_compliance(self):
        page = _mk_page(
            audience="client",
            short_answer="public answer",
        )
        with patch.object(
            read_wiki_page.wiki_repo, "fetch_page", return_value=page
        ):
            result = read_wiki_page.execute(
                _ctx_for_agent("compliance.remediation"),
                category="savings",
                slug="any",
            )
        assert result.get("error") is None
        assert result["short_answer"] == "public answer"


# ─────────────────────────────────────────────────────────────────
# Integration sanity (filesystem réel — s'exécute si data/wiki existe)
# ─────────────────────────────────────────────────────────────────


WIKI_EXISTS = wiki_repo.WIKI_ROOT.exists() and any(
    (wiki_repo.WIKI_ROOT / "faq").glob("*/*.md")
)


@pytest.mark.skipif(
    not WIKI_EXISTS,
    reason="data/wiki not present (Phase 1 storage not run)",
)
class TestFilesystemSanity:
    def test_loads_at_least_200_pages(self):
        n = wiki_repo.total_pages_loaded()
        assert n >= 200, (
            f"Expected ≥ 200 pages from Phase 1 import, got {n}"
        )

    def test_savings_category_has_pages(self):
        out = wiki_repo.list_pages(category="savings", limit=50)
        assert len(out) >= 5

    def test_select_pages_returns_savings_for_vault_query(self):
        out = wiki_repo.select_pages(
            question="how does the flexible vault work",
            top_k=5,
            category="savings",
        )
        # Au moins une fiche savings doit matcher (le wiki contient
        # plusieurs pages explicitement sur "flexible vault").
        assert len(out) >= 1
        for page, score, _ in out:
            assert page.category == "savings"
            assert score > 0

    def test_fetch_page_round_trip(self):
        listed = wiki_repo.list_pages(category="savings", limit=1)
        if not listed:
            pytest.skip("savings category empty")
        first = listed[0]
        page = wiki_repo.fetch_page(
            category=first["category"], slug=first["slug"]
        )
        assert page is not None
        assert page.slug == first["slug"]
        assert page.category == "savings"
