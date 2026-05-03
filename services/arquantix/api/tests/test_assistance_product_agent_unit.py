"""Tests unitaires agent **product** Phase 2c — repo + tools + registry.

Couvre :
  - `product_repo.fetch_knowledge_by_slug` / `list_known_slugs`
  - tool `read_product_knowledge` : not_found, missing_slug, succès
  - tool `list_product_knowledge_topics` : filtrage topic
  - registry : `product` exposé en runtime + tools attendus

Spec : `services/assistance/agents/repositories/product_repo.py`,
`services/assistance/agents/tools/product/`,
`services/assistance/agents/tools/registry.py`.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.repositories import product_repo
from services.assistance.agents.tools import registry as tools_registry
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.product import (
    list_product_knowledge_topics,
    read_product_knowledge,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(*, agent_id: str = "product") -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=None,  # product n'a pas accès au client
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id=agent_id,
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-product",
    )


class TestProductRepo:
    def test_fetch_empty_slug_returns_none(self):
        assert product_repo.fetch_knowledge_by_slug(MagicMock(), slug="") is None

    def test_fetch_repo_error_returns_none(self):
        db = MagicMock()
        db.query.side_effect = RuntimeError("boom")
        assert (
            product_repo.fetch_knowledge_by_slug(db, slug="anything")
            is None
        )

    def test_fetch_returns_normalized_dict(self):
        # On simule la query SQLAlchemy fluide :
        # db.query(...).filter(...).filter(...).one_or_none()
        row = MagicMock()
        row.slug = "deposit_delay_sepa_in"
        row.topic = "delay"
        row.title = "Délai SEPA"
        row.body = "Texte pédagogique"
        row.metadata_json = {"applies_to": "FR/EU"}
        ts = MagicMock()
        ts.isoformat.return_value = "2025-01-01T00:00:00+00:00"
        row.updated_at = ts

        db = MagicMock()
        chain = db.query.return_value
        chain.filter.return_value.filter.return_value.one_or_none.return_value = row

        out = product_repo.fetch_knowledge_by_slug(
            db, slug="deposit_delay_sepa_in"
        )
        assert out is not None
        assert out["slug"] == "deposit_delay_sepa_in"
        assert out["title"] == "Délai SEPA"
        assert out["metadata"] == {"applies_to": "FR/EU"}

    def test_list_returns_minimal_fields(self):
        row = MagicMock()
        row.slug = "withdrawal_delay_sepa_out"
        row.topic = "delay"
        row.title = "Délai retrait"
        db = MagicMock()
        # Sans topic : la chaîne est .query(...).filter(is_active).order_by(...).limit(...).all()
        chain = db.query.return_value
        chain.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            row
        ]
        out = product_repo.list_known_slugs(db, topic=None, limit=10)
        assert out == [
            {
                "slug": "withdrawal_delay_sepa_out",
                "topic": "delay",
                "title": "Délai retrait",
            }
        ]

    def test_list_with_topic_filter(self):
        row = MagicMock()
        row.slug = "vault_definition"
        row.topic = "definition"
        row.title = "Définition Vault"
        db = MagicMock()
        chain = db.query.return_value
        chain.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            row
        ]
        out = product_repo.list_known_slugs(db, topic="definition", limit=10)
        assert len(out) == 1
        assert out[0]["topic"] == "definition"


class TestReadProductKnowledgeTool:
    def test_missing_slug(self):
        result = read_product_knowledge.execute(_ctx(), slug="")
        assert result["error"] == "missing_slug"

    def test_not_found(self):
        with patch.object(
            read_product_knowledge.product_repo,
            "fetch_knowledge_by_slug",
            return_value=None,
        ):
            result = read_product_knowledge.execute(_ctx(), slug="nope")
        assert result["error"] == "not_found"
        assert result["slug"] == "nope"

    def test_success_returns_payload(self):
        payload = {
            "slug": "kyc_review_typical_delay",
            "topic": "delay",
            "title": "KYC delay",
            "body": "Body markdown",
            "metadata": {},
            "updated_at": None,
        }
        with patch.object(
            read_product_knowledge.product_repo,
            "fetch_knowledge_by_slug",
            return_value=payload,
        ):
            result = read_product_knowledge.execute(
                _ctx(), slug="KYC_review_typical_delay"  # noqa
            )
        assert "error" not in result
        assert result["slug"] == "kyc_review_typical_delay"


class TestListProductKnowledgeTopicsTool:
    def test_no_topic_returns_full_list(self):
        rows = [
            {"slug": "a", "topic": "delay", "title": "A"},
            {"slug": "b", "topic": "definition", "title": "B"},
        ]
        with patch.object(
            list_product_knowledge_topics.product_repo,
            "list_known_slugs",
            return_value=rows,
        ):
            result = list_product_knowledge_topics.execute(_ctx())
        assert result["topics"] == rows
        assert result["filtered_by_topic"] is None
        assert result["total"] == 2

    def test_topic_filter_passed_through(self):
        with patch.object(
            list_product_knowledge_topics.product_repo,
            "list_known_slugs",
            return_value=[],
        ) as mock_list:
            list_product_knowledge_topics.execute(_ctx(), topic="DELAY")
        mock_list.assert_called_once_with(
            mock_list.call_args[0][0], topic="delay", limit=100
        )


class TestRegistryHasProduct:
    def test_product_registered_with_runtime_tools(self):
        tool_names = tools_registry.all_tool_names("product")
        assert "read_product_knowledge" in tool_names
        assert "list_product_knowledge_topics" in tool_names
        assert "ask_user_question" in tool_names
        # Phase 2c : product N'A PAS consult_specialist (anti-récursion).
        assert "consult_specialist" not in tool_names
        # Pas de handoff non plus (specialist terminal).
        assert "handoff_to_agent" not in tool_names
