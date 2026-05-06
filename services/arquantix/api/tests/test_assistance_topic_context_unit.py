"""Tests unitaires Cognitive Bot v4 — Lot 4 « Topic mémoire cross-tour »
(2026-05-06).

Couvre :

  * ``ToolContext.current_topic`` :
    - Default à ``None``.
    - Accepte un dict JSON-safe.
    - Reste immuable (dataclass frozen).

  * ``services.assistance.agents.tools.shared.topic_context`` :
    - Helpers défensifs (None, dict vide, kind inconnu, types invalides).
    - Normalisation casing (product_code / instrument_symbol → upper).
    - ``topic_matches_*`` cohérent avec les helpers individuels.
    - ``topic_snapshot`` structurellement stable.
    - Constantes alignées avec ``conversation_topic.TOPIC_ANCHORING_TOOLS``.

  * Plumbing runtime :
    - ``run_agent_loop`` recopie ``memory_state["current_topic"]`` dans
      ``ToolContext.current_topic``.
    - ``_run_consult_specialist`` propage ``current_topic`` au
      sub-runtime via ``memory_state``.

Hors scope :
  * Calcul du topic (cf. ``test_assistance_conversation_topic_unit.py``).
  * Persistance DB (cf. tests d'intégration de
    ``conversation_topic.py``).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared import topic_context
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _ctx(*, topic: dict | None = None) -> ToolContext:
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
        current_topic=topic,
    )


# ─────────────────────────────────────────────────────────────────────
# ToolContext.current_topic
# ─────────────────────────────────────────────────────────────────────


class TestToolContextCurrentTopic:
    def test_default_none(self):
        ctx = ToolContext(
            db=MagicMock(),
            client_id=None,
            person_id=None,
            user_id=1,
            actor_kind=ActorKind.CUSTOMER,
            agent_id="product",
            conversation_id="conv",
            iteration=1,
            audit_session_id="sess",
            correlation_id="corr",
        )
        assert ctx.current_topic is None

    def test_accepts_dict(self):
        topic = {"kind": "instrument", "instrument_symbol": "BTC"}
        ctx = _ctx(topic=topic)
        assert ctx.current_topic == topic

    def test_immutable_field_assignment(self):
        ctx = _ctx(topic={"kind": "instrument", "instrument_symbol": "BTC"})
        with pytest.raises((AttributeError, Exception)):
            ctx.current_topic = {"kind": "vancelian_product"}  # type: ignore[misc]

    def test_independent_from_cognitive_state(self):
        """Régression : current_topic ne doit pas être confondu avec
        cognitive_state (les deux sont des dicts dans memory_state)."""
        cog = {"emotional_intent": "fear"}
        topic = {"kind": "instrument", "instrument_symbol": "BTC"}
        ctx = ToolContext(
            db=MagicMock(),
            client_id=None,
            person_id=None,
            user_id=1,
            actor_kind=ActorKind.CUSTOMER,
            agent_id="product",
            conversation_id="conv",
            iteration=1,
            audit_session_id="sess",
            correlation_id="corr",
            cognitive_state=cog,
            current_topic=topic,
        )
        assert ctx.cognitive_state == cog
        assert ctx.current_topic == topic


# ─────────────────────────────────────────────────────────────────────
# Helpers : has_current_topic + get_current_topic_kind
# ─────────────────────────────────────────────────────────────────────


class TestKindHelpers:
    @pytest.mark.parametrize(
        "topic,expected",
        [
            (None, None),
            ({}, None),
            ({"kind": "vancelian_product"}, "vancelian_product"),
            ({"kind": "instrument"}, "instrument"),
            ({"kind": "topic_other"}, "topic_other"),
            ({"kind": "INSTRUMENT"}, "instrument"),  # case-insensitive
            ({"kind": "  instrument  "}, "instrument"),  # trim
            ({"kind": "unknown_kind"}, None),
            ({"kind": 42}, None),
            ({"kind": None}, None),
            ("not_a_dict", None),
        ],
    )
    def test_get_current_topic_kind(self, topic, expected):
        ctx = _ctx(topic=topic if isinstance(topic, dict) else None)
        if topic == "not_a_dict":
            # Force un type invalide via object.__setattr__ pour
            # bypass frozen=True (cas pathologique de test).
            object.__setattr__(ctx, "current_topic", "not_a_dict")
        assert topic_context.get_current_topic_kind(ctx) == expected

    def test_has_current_topic(self):
        assert topic_context.has_current_topic(_ctx(topic=None)) is False
        assert topic_context.has_current_topic(_ctx(topic={})) is False
        assert (
            topic_context.has_current_topic(
                _ctx(topic={"kind": "instrument"})
            )
            is True
        )


# ─────────────────────────────────────────────────────────────────────
# Helpers : product_code / instrument_symbol
# ─────────────────────────────────────────────────────────────────────


class TestProductCodeHelpers:
    def test_returns_none_when_kind_is_instrument(self):
        ctx = _ctx(
            topic={
                "kind": "instrument",
                "product_code": "TOP5",  # ignoré car wrong kind
            }
        )
        assert topic_context.get_current_topic_product_code(ctx) is None

    def test_returns_uppercase(self):
        ctx = _ctx(
            topic={"kind": "vancelian_product", "product_code": "top5"}
        )
        assert topic_context.get_current_topic_product_code(ctx) == "TOP5"

    def test_returns_none_when_empty(self):
        ctx = _ctx(
            topic={"kind": "vancelian_product", "product_code": "   "}
        )
        assert topic_context.get_current_topic_product_code(ctx) is None

    def test_returns_none_when_missing(self):
        ctx = _ctx(topic={"kind": "vancelian_product"})
        assert topic_context.get_current_topic_product_code(ctx) is None


class TestInstrumentSymbolHelpers:
    def test_returns_none_when_kind_is_product(self):
        ctx = _ctx(
            topic={
                "kind": "vancelian_product",
                "instrument_symbol": "BTC",
            }
        )
        assert (
            topic_context.get_current_topic_instrument_symbol(ctx) is None
        )

    def test_returns_uppercase(self):
        ctx = _ctx(
            topic={"kind": "instrument", "instrument_symbol": "btc"}
        )
        assert (
            topic_context.get_current_topic_instrument_symbol(ctx) == "BTC"
        )

    def test_returns_none_when_missing(self):
        ctx = _ctx(topic={"kind": "instrument"})
        assert (
            topic_context.get_current_topic_instrument_symbol(ctx) is None
        )


# ─────────────────────────────────────────────────────────────────────
# Helpers : agent_owner + label
# ─────────────────────────────────────────────────────────────────────


class TestOwnerAndLabel:
    def test_agent_owner_present(self):
        ctx = _ctx(
            topic={"kind": "instrument", "agent_owner": "product"}
        )
        assert (
            topic_context.get_current_topic_agent_owner(ctx) == "product"
        )

    def test_agent_owner_missing(self):
        ctx = _ctx(topic={"kind": "instrument"})
        assert topic_context.get_current_topic_agent_owner(ctx) is None

    def test_label_for_vancelian_product(self):
        ctx = _ctx(
            topic={
                "kind": "vancelian_product",
                "product_code": "TOP5",
                "agent_owner": "product",
            }
        )
        assert (
            topic_context.get_current_topic_label(ctx)
            == "vancelian_product:TOP5"
        )

    def test_label_for_instrument(self):
        ctx = _ctx(
            topic={
                "kind": "instrument",
                "instrument_symbol": "BTC",
                "agent_owner": "product",
            }
        )
        assert (
            topic_context.get_current_topic_label(ctx) == "instrument:BTC"
        )

    def test_label_for_topic_other_with_wiki_slug(self):
        ctx = _ctx(
            topic={
                "kind": "topic_other",
                "wiki_slug": "delays-sepa",
                "wiki_category": "faq",
                "agent_owner": "product",
            }
        )
        assert (
            topic_context.get_current_topic_label(ctx)
            == "topic_other:delays-sepa"
        )

    def test_label_for_topic_other_without_slug(self):
        ctx = _ctx(
            topic={"kind": "topic_other", "agent_owner": "product"}
        )
        assert (
            topic_context.get_current_topic_label(ctx) == "topic_other"
        )

    def test_label_none_when_no_topic(self):
        assert topic_context.get_current_topic_label(_ctx()) is None


# ─────────────────────────────────────────────────────────────────────
# Helpers : topic_matches_*
# ─────────────────────────────────────────────────────────────────────


class TestTopicMatches:
    def test_product_code_match(self):
        ctx = _ctx(
            topic={"kind": "vancelian_product", "product_code": "TOP5"}
        )
        assert topic_context.topic_matches_product_code(ctx, "top5") is True
        assert topic_context.topic_matches_product_code(ctx, "TOP5") is True
        assert topic_context.topic_matches_product_code(ctx, "ALT5") is False
        assert topic_context.topic_matches_product_code(ctx, None) is False
        assert topic_context.topic_matches_product_code(ctx, "") is False

    def test_product_code_mismatch_when_topic_is_instrument(self):
        ctx = _ctx(
            topic={
                "kind": "instrument",
                "instrument_symbol": "BTC",
                "product_code": "TOP5",
            }
        )
        # product_code dans le payload mais kind=instrument → no match.
        assert (
            topic_context.topic_matches_product_code(ctx, "TOP5") is False
        )

    def test_instrument_symbol_match(self):
        ctx = _ctx(
            topic={"kind": "instrument", "instrument_symbol": "BTC"}
        )
        assert (
            topic_context.topic_matches_instrument_symbol(ctx, "btc")
            is True
        )
        assert (
            topic_context.topic_matches_instrument_symbol(ctx, "ETH")
            is False
        )
        assert (
            topic_context.topic_matches_instrument_symbol(ctx, None) is False
        )

    def test_no_topic_never_matches(self):
        ctx = _ctx(topic=None)
        assert (
            topic_context.topic_matches_product_code(ctx, "TOP5") is False
        )
        assert (
            topic_context.topic_matches_instrument_symbol(ctx, "BTC")
            is False
        )


# ─────────────────────────────────────────────────────────────────────
# topic_snapshot
# ─────────────────────────────────────────────────────────────────────


class TestTopicSnapshot:
    def test_snapshot_structure_when_present(self):
        ctx = _ctx(
            topic={
                "kind": "instrument",
                "instrument_symbol": "BTC",
                "agent_owner": "product",
            }
        )
        snap = topic_context.topic_snapshot(ctx)
        assert set(snap.keys()) == {
            "has_topic",
            "kind",
            "label",
            "agent_owner",
        }
        assert snap["has_topic"] is True
        assert snap["kind"] == "instrument"
        assert snap["label"] == "instrument:BTC"
        assert snap["agent_owner"] == "product"

    def test_snapshot_when_none(self):
        snap = topic_context.topic_snapshot(_ctx())
        assert snap == {
            "has_topic": False,
            "kind": None,
            "label": None,
            "agent_owner": None,
        }

    def test_snapshot_is_json_safe(self):
        import json

        ctx = _ctx(
            topic={
                "kind": "vancelian_product",
                "product_code": "TOP5",
                "agent_owner": "product",
            }
        )
        snap = topic_context.topic_snapshot(ctx)
        # Doit pouvoir round-tripper en JSON sans erreur.
        encoded = json.dumps(snap)
        assert json.loads(encoded) == snap


# ─────────────────────────────────────────────────────────────────────
# Constantes : alignement avec conversation_topic.py
# ─────────────────────────────────────────────────────────────────────


class TestConstantsAlignment:
    def test_known_kinds_aligned_with_anchoring_tools(self):
        """Les ``KNOWN_TOPIC_KINDS`` doivent au moins inclure tous les
        kinds émis par ``infer_topic_from_tool_call`` (cf.
        ``TOPIC_ANCHORING_TOOLS``)."""
        from services.assistance import conversation_topic

        emitted_kinds = set(conversation_topic.TOPIC_ANCHORING_TOOLS.values())
        assert emitted_kinds.issubset(topic_context.KNOWN_TOPIC_KINDS)


# ─────────────────────────────────────────────────────────────────────
# Plumbing runtime — run_agent_loop recopie current_topic dans ToolContext
# ─────────────────────────────────────────────────────────────────────


class TestRuntimePlumbing:
    """Ces tests sont des smoke tests du chemin
    ``memory_state["current_topic"] -> ToolContext.current_topic`` —
    via une lecture de la branche du code dans agent_loop.py.

    On ne lance pas le loop complet (lourd), on vérifie que la
    construction du ``ToolContext`` lit bien la clé via une
    intercession du constructeur.
    """

    def test_agent_loop_reads_current_topic_from_memory_state(
        self, monkeypatch
    ):
        """Smoke test : on vérifie que dans le module ``agent_loop``,
        la construction du ``ToolContext`` est bien faite avec
        ``current_topic=memory_state.get("current_topic")``.

        On le valide structurellement en lisant le source (pour ne
        pas avoir à monter un agent loop complet ici)."""
        import inspect

        from services.assistance.agents.runtime import agent_loop

        src = inspect.getsource(agent_loop.run_agent_loop)
        assert "current_topic=topic_dict" in src
        assert "memory_state.get(\"current_topic\")" in src

    def test_consult_specialist_propagates_current_topic(self):
        """Smoke test : ``_run_consult_specialist`` doit propager
        ``current_topic`` au sub_input.memory_state."""
        import inspect

        from services.assistance.agents.runtime import agent_loop

        src = inspect.getsource(agent_loop._run_consult_specialist)
        assert (
            "\"current_topic\": caller_mem.get(\"current_topic\")" in src
        )
