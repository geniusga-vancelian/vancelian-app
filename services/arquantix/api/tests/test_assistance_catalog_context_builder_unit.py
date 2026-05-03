"""Tests unitaires du builder ``catalog_context_builder``.

Couvre :
  - format de la section *types de transactions* (ordre, colonnes, codes)
  - format de la section *produits documentés* (filtre `product_basics_*`)
  - bloc complet (en-tête + règle d'usage)
  - cache TTL 60 s + ``invalidate_cache``
  - kill-switch ``ASSISTANCE_AGENT_CATALOG_CONTEXT_DISABLED``
  - whitelist d'agents (``should_inject_catalog_for_agent``)
  - best-effort sur erreur DB → renvoie ``None`` sans propager

Tests sans réseau ni DB réelle : SQLAlchemy est mocké via ``MagicMock``.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from services.assistance.agents.runtime import catalog_context_builder as ccb


def _row(slug: str, topic: str, title: str, metadata: dict[str, Any] | None = None):
    """Fabrique une fausse row ``ProductKnowledge`` (duck-typing suffisant)."""
    r = MagicMock()
    r.slug = slug
    r.topic = topic
    r.title = title
    r.metadata_json = metadata or {}
    return r


def _patch_query(monkeypatch, rows_by_topic: dict[str, list[Any]]):
    """Patch ``_query_knowledge_rows`` du builder pour retourner les rows par topic.

    Approche plus robuste qu'un mock SQLAlchemy fluide : on intercepte au niveau
    du repository interne (bord net entre la logique de formatage et l'I/O DB).
    """
    def fake(_db, topic):
        return rows_by_topic.get(topic, [])

    monkeypatch.setattr(ccb, "_query_knowledge_rows", fake)
    # La session DB est inutilisée par fake mais le builder en demande une.
    return MagicMock()


@pytest.fixture(autouse=True)
def _reset_cache_and_env(monkeypatch):
    monkeypatch.delenv("ASSISTANCE_AGENT_CATALOG_CONTEXT_DISABLED", raising=False)
    ccb.invalidate_cache()
    yield
    ccb.invalidate_cache()


class TestTransactionKindsSection:
    def test_orders_by_display_order_then_code(self):
        rows = [
            _row(
                slug="kind_buy_crypto",
                topic="transaction_kind",
                title="Achat crypto",
                metadata={
                    "code": "buy_crypto",
                    "label_fr": "Achat crypto",
                    "direction": "trade",
                    "linked_knowledge_slug": "swap_settlement_immediate",
                    "display_order": 60,
                },
            ),
            _row(
                slug="kind_deposit_sepa",
                topic="transaction_kind",
                title="Dépôt SEPA",
                metadata={
                    "code": "deposit_sepa",
                    "label_fr": "Dépôt par virement SEPA",
                    "direction": "in",
                    "linked_knowledge_slug": "deposit_delay_sepa_in",
                    "display_order": 10,
                },
            ),
        ]
        out = ccb._format_transaction_kinds_section(rows)
        assert out is not None
        # Structure attendue: titre / blank / header / separator / data...
        # On vérifie que la 1ère ligne de données contient deposit_sepa (display_order=10).
        data_lines = [
            line for line in out.splitlines()
            if line.startswith("| `")
        ]
        assert data_lines, "no data lines in section"
        assert "deposit_sepa" in data_lines[0]
        assert "buy_crypto" in data_lines[1]

    def test_skips_rows_without_code(self):
        rows = [
            _row(
                slug="kind_orphan",
                topic="transaction_kind",
                title="Ligne incomplète",
                metadata={"label_fr": "Sans code"},
            ),
            _row(
                slug="kind_ok",
                topic="transaction_kind",
                title="OK",
                metadata={
                    "code": "deposit_sepa",
                    "direction": "in",
                    "linked_knowledge_slug": "deposit_delay_sepa_in",
                },
            ),
        ]
        out = ccb._format_transaction_kinds_section(rows)
        assert out is not None
        assert "Sans code" not in out
        assert "deposit_sepa" in out

    def test_returns_none_if_no_rows(self):
        assert ccb._format_transaction_kinds_section([]) is None


class TestProductsSection:
    def test_only_product_basics_slugs_are_kept(self):
        rows = [
            _row(slug="product_basics_vault", topic="definition", title="Coffre"),
            _row(slug="kyc_overview", topic="definition", title="Aperçu KYC"),
        ]
        out = ccb._format_products_section(rows)
        assert out is not None
        assert "vault" in out
        assert "kyc_overview" not in out

    def test_exclude_from_catalog_metadata_filters_row(self):
        rows = [
            _row(
                slug="product_basics_internal_test",
                topic="definition",
                title="Test interne",
                metadata={"exclude_from_catalog": True},
            ),
        ]
        assert ccb._format_products_section(rows) is None

    def test_strips_product_basics_prefix_in_code_column(self):
        rows = [
            _row(slug="product_basics_scpi", topic="definition", title="SCPI"),
        ]
        out = ccb._format_products_section(rows)
        assert out is not None
        # Le code affiché est le suffixe sans "product_basics_"
        assert "| `scpi` |" in out
        # Mais la colonne knowledge garde le slug complet (utile pour le LLM)
        assert "`product_basics_scpi`" in out


class TestFullBlock:
    def test_returns_none_when_both_sections_empty(self):
        assert ccb._format_block(None, None) is None

    def test_includes_usage_rule_and_header(self):
        out = ccb._format_block(
            transaction_kinds_md="### Types de transactions supportées\n…",
            products_md=None,
        )
        assert out is not None
        assert "Catalogue Vancelian" in out
        assert "read_product_knowledge" in out
        assert "consult_specialist" in out


class TestBuildCatalogContextBlock:
    def test_full_pipeline_returns_block_with_both_sections(self, monkeypatch):
        db = _patch_query(monkeypatch, {
            "transaction_kind": [
                _row(
                    slug="kind_buy_crypto",
                    topic="transaction_kind",
                    title="Achat crypto",
                    metadata={
                        "code": "buy_crypto",
                        "direction": "trade",
                        "linked_knowledge_slug": "swap_settlement_immediate",
                        "display_order": 60,
                    },
                ),
            ],
            "definition": [
                _row(slug="product_basics_vault", topic="definition", title="Coffre"),
            ],
        })
        block = ccb.build_catalog_context_block(db)
        assert block is not None
        assert "buy_crypto" in block
        assert "vault" in block

    def test_empty_db_returns_none(self, monkeypatch):
        db = _patch_query(monkeypatch, {"transaction_kind": [], "definition": []})
        assert ccb.build_catalog_context_block(db) is None

    def test_db_error_returns_none_without_propagating(self):
        db = MagicMock()
        db.query.side_effect = RuntimeError("db down")
        # Le builder swallow l'exception en best-effort (via _query_knowledge_rows).
        assert ccb.build_catalog_context_block(db) is None

    def test_cache_hits_within_ttl(self, monkeypatch):
        call_counter = {"n": 0}

        def fake(_db, topic):
            call_counter["n"] += 1
            if topic == "transaction_kind":
                return [_row(
                    slug="k",
                    topic="transaction_kind",
                    title="x",
                    metadata={"code": "c", "direction": "in", "linked_knowledge_slug": "s"},
                )]
            return []

        monkeypatch.setattr(ccb, "_query_knowledge_rows", fake)
        db = MagicMock()

        first = ccb.build_catalog_context_block(db)
        n_first = call_counter["n"]
        second = ccb.build_catalog_context_block(db)
        assert first == second
        # 2nd appel = cache hit, donc le compteur n'a pas bougé.
        assert call_counter["n"] == n_first

    def test_invalidate_cache_forces_requery(self, monkeypatch):
        call_counter = {"n": 0}

        def fake(_db, topic):
            call_counter["n"] += 1
            if topic == "transaction_kind":
                return [_row(
                    slug="k",
                    topic="transaction_kind",
                    title="x",
                    metadata={"code": "c", "direction": "in", "linked_knowledge_slug": "s"},
                )]
            return []

        monkeypatch.setattr(ccb, "_query_knowledge_rows", fake)
        db = MagicMock()
        ccb.build_catalog_context_block(db)
        n_before = call_counter["n"]
        ccb.invalidate_cache()
        ccb.build_catalog_context_block(db)
        assert call_counter["n"] > n_before

    def test_kill_switch_disables_block(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_AGENT_CATALOG_CONTEXT_DISABLED", "1")
        db = _patch_query(monkeypatch, {
            "transaction_kind": [
                _row(
                    slug="k",
                    topic="transaction_kind",
                    title="x",
                    metadata={"code": "c", "direction": "in", "linked_knowledge_slug": "s"},
                ),
            ],
            "definition": [],
        })
        assert ccb.build_catalog_context_block(db) is None


class TestShouldInjectCatalogForAgent:
    @pytest.mark.parametrize("agent_id", [
        "router", "compliance.transactional", "compliance.general",
        "advisor", "product", "market",
    ])
    def test_whitelisted_agents_receive_block(self, agent_id):
        assert ccb.should_inject_catalog_for_agent(agent_id) is True

    @pytest.mark.parametrize("agent_id", [
        "summarizer", "default", "compliance.remediation",
        "compliance.registration", "", None,
    ])
    def test_other_agents_do_not_receive_block(self, agent_id):
        assert ccb.should_inject_catalog_for_agent(agent_id) is False

    def test_kill_switch_overrides_whitelist(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_AGENT_CATALOG_CONTEXT_DISABLED", "1")
        assert ccb.should_inject_catalog_for_agent("router") is False
