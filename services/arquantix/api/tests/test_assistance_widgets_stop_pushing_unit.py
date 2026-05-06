"""Tests unitaires Cognitive Bot v4 — Lot 3 « Widgets unifiés »
(2026-05-06).

Couvre uniquement le **garde-fou ``should_stop_pushing``** branché sur
les 3 widgets commerciaux :

    * ``show_instrument_card`` (carte instrument avec CTAs Acheter/
      Vendre)
    * ``show_crypto_bundles`` (slider catalogue bundles avec CTAs
      « Investir »)
    * ``show_bundle_detail`` (fiche bundle avec CTAs « Voir » +
      « Investir »)

Hors scope (couvert ailleurs) :
    * Logique nominale des widgets : cf.
      ``test_assistance_show_crypto_bundles_unit.py``,
      ``test_assistance_show_bundle_detail_unit.py``,
      ``test_assistance_show_instrument_card_unit.py``.
    * Calcul de ``should_stop_pushing`` : cf.
      ``test_assistance_cognitive_context_unit.py``.

Ce fichier vérifie uniquement le **branchement** (court-circuit avant
toute requête DB/marché, payload typé `stop_pushing_active`,
`embeds_to_emit` vide, hint exploitable par le LLM).

Décision design Lot 3 documentée :
    * Les 3 widgets retournent ``error: stop_pushing_active`` (pas
      d'embed émis) plutôt que de filtrer les CTAs Buy/Sell. Raison :
      un client en FEAR n'a pas seulement besoin de moins de CTAs ;
      il a besoin que le bot **ne pousse pas du tout** un produit et
      passe en mode rassurance/preuves. Filtrer la moitié des CTAs
      n'aurait pas adressé le vrai besoin (rassurance verbale).
    * Le garde-fou est branché AVANT toute requête (catalog DB, market
      data) — gain de latence, économie de tokens log.
    * Les widgets purement informatifs (``show_top_movers``,
      ``show_featured_articles``) ne reçoivent **PAS** ce garde-fou :
      leur rôle est d'informer, pas de pousser un instrument précis.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.product import (
    show_bundle_detail,
    show_crypto_bundles,
    show_instrument_card,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─────────────────────────────────────────────────────────────────────
# Helpers : construction de ToolContext avec/sans cognitive state
# ─────────────────────────────────────────────────────────────────────


def _make_ctx(
    *,
    cognitive_state: dict | None = None,
    objective: dict | None = None,
    agent_id: str = "product",
) -> ToolContext:
    """ToolContext minimal — la DB est mockée car le garde-fou doit
    court-circuiter AVANT tout appel DB. Si un test voit une trace
    d'appel sur ``ctx.db``, c'est que le garde-fou est mal placé.
    """
    return ToolContext(
        db=MagicMock(),
        client_id=None,
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id=agent_id,
        conversation_id=str(uuid4()),
        iteration=1,
        audit_session_id=str(uuid4()),
        correlation_id=str(uuid4()),
        cognitive_state=cognitive_state,
        objective=objective,
    )


def _fear_state() -> dict:
    return {
        "emotional_intent": "fear",
        "conversation_stage": "discovery",
        "trust_level": 0.3,
        "knowledge_level": "low",
    }


def _anger_state() -> dict:
    return {
        "emotional_intent": "anger",
        "conversation_stage": "discovery",
        "trust_level": 0.2,
        "knowledge_level": "medium",
    }


def _curiosity_state() -> dict:
    return {
        "emotional_intent": "curiosity",
        "conversation_stage": "discovery",
        "trust_level": 0.6,
        "knowledge_level": "low",
    }


def _objective_stop() -> dict:
    return {
        "primary_goal": "reassure",
        "next_best_action": "give_proof",
        "stop_pushing": True,
    }


def _objective_dont_stop() -> dict:
    return {
        "primary_goal": "inform",
        "next_best_action": "recommend",
        "stop_pushing": False,
    }


# ─────────────────────────────────────────────────────────────────────
# show_instrument_card
# ─────────────────────────────────────────────────────────────────────


class TestShowInstrumentCardStopPushing:
    """Garde-fou ``stop_pushing`` sur ``show_instrument_card``.

    Le widget affiche une carte avec CTAs Buy/Sell — push commercial
    inacceptable quand le client est en FEAR/ANGER ou que l'objectif
    explicite est ``stop_pushing=True``.
    """

    def test_fear_short_circuits_before_db(self):
        ctx = _make_ctx(cognitive_state=_fear_state())
        result = show_instrument_card.execute(ctx, symbol="BTC")
        assert result["error"] == "stop_pushing_active"
        assert result["emotional_intent"] == "fear"
        assert "hint" in result and isinstance(result["hint"], str)
        assert "Acheter" in result["hint"] or "rassurance" in result["hint"]
        assert ctx.embeds_to_emit == []
        # Aucune requête DB ne doit avoir été tentée.
        ctx.db.query.assert_not_called()

    def test_anger_short_circuits_before_db(self):
        ctx = _make_ctx(cognitive_state=_anger_state())
        result = show_instrument_card.execute(ctx, symbol="ETH")
        assert result["error"] == "stop_pushing_active"
        assert result["emotional_intent"] == "anger"
        assert ctx.embeds_to_emit == []
        ctx.db.query.assert_not_called()

    def test_explicit_objective_stop_pushing_overrides_neutral(self):
        """Même si l'émotion n'est pas urgente, l'objective explicite
        ``stop_pushing=True`` doit court-circuiter (cf. design helper
        ``should_stop_pushing`` priorité 1)."""
        ctx = _make_ctx(
            cognitive_state=_curiosity_state(),
            objective=_objective_stop(),
        )
        result = show_instrument_card.execute(ctx, symbol="SOL")
        assert result["error"] == "stop_pushing_active"
        assert ctx.embeds_to_emit == []
        ctx.db.query.assert_not_called()

    def test_curiosity_does_not_block(self, monkeypatch):
        """En curiosity sans objective.stop_pushing, le widget doit
        suivre son flux normal (et planter sur l'absence de market
        data, ce qui prouve que le garde-fou ne s'est pas déclenché)."""
        ctx = _make_ctx(
            cognitive_state=_curiosity_state(),
            objective=_objective_dont_stop(),
        )

        def _fake_query(_):
            mock = MagicMock()
            mock.filter.return_value.first.return_value = None
            return mock

        ctx.db.query.side_effect = _fake_query
        result = show_instrument_card.execute(ctx, symbol="BTC")
        # Pas de stop_pushing : on tombe sur ``unsupported_instrument``
        # (mock _resolve_instrument retourne None) — preuve que le
        # garde-fou a laissé passer.
        assert result.get("error") != "stop_pushing_active"

    def test_no_cognitive_state_does_not_block(self, monkeypatch):
        """Si ``ctx.cognitive_state`` est ``None`` (cas test / startup
        avant calcul cognitif), le défaut neutral doit laisser passer.
        """
        ctx = _make_ctx(cognitive_state=None, objective=None)
        ctx.db.query.return_value.filter.return_value.first.return_value = None
        result = show_instrument_card.execute(ctx, symbol="BTC")
        assert result.get("error") != "stop_pushing_active"

    def test_missing_symbol_still_returns_proper_error_when_pushing_ok(self):
        """Quand le garde-fou laisse passer, l'erreur de validation
        normale (``missing_symbol``) doit toujours fonctionner."""
        ctx = _make_ctx(cognitive_state=None)
        result = show_instrument_card.execute(ctx, symbol="")
        assert result["error"] == "missing_symbol"

    def test_fear_blocks_before_symbol_validation(self):
        """Garantit que le garde-fou est bien EN PREMIER : même un
        symbol vide ne doit pas court-circuiter avant ``stop_pushing``
        (sinon on perd l'info pour le LLM)."""
        ctx = _make_ctx(cognitive_state=_fear_state())
        result = show_instrument_card.execute(ctx, symbol="")
        assert result["error"] == "stop_pushing_active"


# ─────────────────────────────────────────────────────────────────────
# show_crypto_bundles
# ─────────────────────────────────────────────────────────────────────


class TestShowCryptoBundlesStopPushing:
    """Garde-fou sur ``show_crypto_bundles`` (slider catalogue)."""

    def test_fear_short_circuits_before_catalog(self, monkeypatch):
        ctx = _make_ctx(cognitive_state=_fear_state())
        # Si le tool appelait CatalogService alors qu'il est censé
        # court-circuiter, le test exploserait avec AttributeError sur
        # le MagicMock — preuve indirecte. On le rend explicite via
        # un patch agressif :
        called = {"catalog": False}

        class _CatalogSentinel:
            def get_public_catalog(self, *_args, **_kwargs):
                called["catalog"] = True
                raise AssertionError(
                    "CatalogService doit être court-circuité par "
                    "stop_pushing en amont."
                )

        monkeypatch.setattr(
            show_crypto_bundles, "CatalogService", _CatalogSentinel
        )
        result = show_crypto_bundles.execute(ctx)
        assert result["error"] == "stop_pushing_active"
        assert result["emotional_intent"] == "fear"
        assert ctx.embeds_to_emit == []
        assert called["catalog"] is False

    def test_anger_short_circuits(self, monkeypatch):
        ctx = _make_ctx(cognitive_state=_anger_state())

        class _CatalogSentinel:
            def get_public_catalog(self, *_args, **_kwargs):
                raise AssertionError("must not be called")

        monkeypatch.setattr(
            show_crypto_bundles, "CatalogService", _CatalogSentinel
        )
        result = show_crypto_bundles.execute(ctx)
        assert result["error"] == "stop_pushing_active"
        assert ctx.embeds_to_emit == []

    def test_explicit_stop_pushing_objective(self, monkeypatch):
        ctx = _make_ctx(
            cognitive_state=_curiosity_state(),
            objective=_objective_stop(),
        )

        class _CatalogSentinel:
            def get_public_catalog(self, *_args, **_kwargs):
                raise AssertionError("must not be called")

        monkeypatch.setattr(
            show_crypto_bundles, "CatalogService", _CatalogSentinel
        )
        result = show_crypto_bundles.execute(ctx)
        assert result["error"] == "stop_pushing_active"

    def test_curiosity_does_not_block(self, monkeypatch):
        ctx = _make_ctx(
            cognitive_state=_curiosity_state(),
            objective=_objective_dont_stop(),
        )

        class _CatalogEmpty:
            def get_public_catalog(self, *_args, **_kwargs):
                return []

        monkeypatch.setattr(
            show_crypto_bundles, "CatalogService", _CatalogEmpty
        )
        result = show_crypto_bundles.execute(ctx)
        # Pas de stop_pushing : le tool s'exécute normalement et
        # tombe sur catalogue vide (note: no_active_bundle).
        assert result.get("error") != "stop_pushing_active"
        assert result.get("note") == "no_active_bundle"


# ─────────────────────────────────────────────────────────────────────
# show_bundle_detail
# ─────────────────────────────────────────────────────────────────────


class TestShowBundleDetailStopPushing:
    """Garde-fou sur ``show_bundle_detail`` (fiche bundle ciblée)."""

    def test_fear_short_circuits_before_catalog(self, monkeypatch):
        ctx = _make_ctx(cognitive_state=_fear_state())

        class _CatalogSentinel:
            def get_public_catalog(self, *_args, **_kwargs):
                raise AssertionError("must not be called")

        monkeypatch.setattr(
            show_bundle_detail, "CatalogService", _CatalogSentinel
        )
        result = show_bundle_detail.execute(ctx, product_code="TOP5")
        assert result["error"] == "stop_pushing_active"
        assert result["emotional_intent"] == "fear"
        assert ctx.embeds_to_emit == []

    def test_anger_short_circuits(self, monkeypatch):
        ctx = _make_ctx(cognitive_state=_anger_state())

        class _CatalogSentinel:
            def get_public_catalog(self, *_args, **_kwargs):
                raise AssertionError("must not be called")

        monkeypatch.setattr(
            show_bundle_detail, "CatalogService", _CatalogSentinel
        )
        result = show_bundle_detail.execute(ctx, product_code="ALT5")
        assert result["error"] == "stop_pushing_active"

    def test_fear_blocks_before_identifier_validation(self, monkeypatch):
        """Garde-fou en premier : même sans identifier, on doit voir
        ``stop_pushing_active`` (pas ``missing_identifier``)."""
        ctx = _make_ctx(cognitive_state=_fear_state())

        class _CatalogSentinel:
            def get_public_catalog(self, *_args, **_kwargs):
                raise AssertionError("must not be called")

        monkeypatch.setattr(
            show_bundle_detail, "CatalogService", _CatalogSentinel
        )
        result = show_bundle_detail.execute(ctx)
        assert result["error"] == "stop_pushing_active"

    def test_curiosity_does_not_block(self, monkeypatch):
        ctx = _make_ctx(
            cognitive_state=_curiosity_state(),
            objective=_objective_dont_stop(),
        )

        class _CatalogEmpty:
            def get_public_catalog(self, *_args, **_kwargs):
                return []

        monkeypatch.setattr(
            show_bundle_detail, "CatalogService", _CatalogEmpty
        )
        result = show_bundle_detail.execute(ctx, product_code="TOP5")
        assert result.get("error") == "no_active_bundle"


# ─────────────────────────────────────────────────────────────────────
# Cohérence : les widgets informatifs ne sont PAS bloqués
# ─────────────────────────────────────────────────────────────────────


class TestInformationalWidgetsNotBlocked:
    """Régression : ``show_top_movers`` et ``show_featured_articles``
    doivent rester accessibles même en FEAR/ANGER.

    Justification : ces widgets sont **informatifs** (top movers du
    marché, articles à la une) ; ils n'ont pas de CTA d'achat. Au
    contraire, en FEAR un client peut vouloir voir des analyses
    factuelles. Les bloquer serait un anti-pattern.
    """

    def test_show_top_movers_module_does_not_import_stop_pushing(self):
        """Garantit qu'on n'a pas branché par erreur le garde-fou sur
        un widget informatif."""
        from services.assistance.agents.tools.market import (
            show_top_movers,
        )

        # Le module ne doit pas importer ``should_stop_pushing``
        # (sinon Lot 3 aurait scope-creep côté informationnel).
        src_attrs = dir(show_top_movers)
        assert "should_stop_pushing" not in src_attrs

    def test_show_featured_articles_module_does_not_import_stop_pushing(
        self,
    ):
        from services.assistance.agents.tools.market import (
            show_featured_articles,
        )

        src_attrs = dir(show_featured_articles)
        assert "should_stop_pushing" not in src_attrs


# ─────────────────────────────────────────────────────────────────────
# Cohérence du payload retourné (contrat LLM)
# ─────────────────────────────────────────────────────────────────────


class TestStopPushingPayloadShape:
    """Le payload ``stop_pushing_active`` doit être stable et exploitable
    par le LLM côté ``agent_loop`` — sinon les régressions silencieuses
    casseraient la chaîne de prompts qui s'appuie sur ces hints.
    """

    @pytest.mark.parametrize(
        "tool_module,kwargs",
        [
            (show_instrument_card, {"symbol": "BTC"}),
            (show_crypto_bundles, {}),
            (show_bundle_detail, {"product_code": "TOP5"}),
        ],
    )
    def test_payload_has_stable_shape(
        self, tool_module, kwargs, monkeypatch
    ):
        ctx = _make_ctx(cognitive_state=_fear_state())
        # Sentinelles pour les widgets qui appellent CatalogService.
        if hasattr(tool_module, "CatalogService"):

            class _Sentinel:
                def get_public_catalog(self, *_a, **_kw):
                    raise AssertionError("must not be called")

            monkeypatch.setattr(tool_module, "CatalogService", _Sentinel)

        result = tool_module.execute(ctx, **kwargs)
        assert isinstance(result, dict)
        assert result.get("error") == "stop_pushing_active"
        assert result.get("emotional_intent") in {"fear", "anger"}
        assert isinstance(result.get("hint"), str)
        assert len(result["hint"]) > 30  # hint utile, pas un placeholder
        # Pas d'embed émis dans aucun cas.
        assert ctx.embeds_to_emit == []
