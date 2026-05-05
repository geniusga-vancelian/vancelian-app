"""Tests unitaires d'intégration des 3 modifications router v2 dans
les parsers ``_parse_redirect_off_topic`` et ``_parse_ask_clarification``.

Couvre le wiring entre :
  * Lot 1 (off-topic fixed list + slot resume).
  * Lot 3 (hybrid clarification : tag override LLM).

Ne fait PAS d'appel LLM réel — on teste uniquement la couche de parsing
des arguments de tool call (déterministe, instantané).
"""

from __future__ import annotations

import pytest

from services.assistance.agents.router import (
    _parse_ask_clarification,
    _parse_redirect_off_topic,
)


class TestRedirectOffTopicFixedList:
    def test_uses_fixed_list_ignoring_llm_options(self):
        # Le LLM peut envoyer n'importe quoi dans options — on substitue
        # toujours par la liste fixe.
        decision = _parse_redirect_off_topic(
            args={
                "bridge": "Sur la météo, ce n'est pas notre sujet ici.",
                "options": [
                    {"id": "default", "label": "Discuter de Vancelian"},
                    {"id": "fake", "label": "Foo"},
                ],
            },
            confidence_min=0.5,
        )
        assert decision.redirect_bridge is not None
        assert "météo" in decision.redirect_bridge.lower()
        # Les options fixes : 5 entrées exactement.
        assert len(decision.fallback_choices) == 5
        ids = [c.id for c in decision.fallback_choices]
        # Pas de "fake" qui aurait été envoyé par le LLM.
        assert "fake" not in ids
        # Les agents experts doivent tous être présents.
        assert "compliance" in ids
        assert "product" in ids
        assert "advisor" in ids
        assert "market" in ids

    def test_resume_slot_added_with_topic(self):
        decision = _parse_redirect_off_topic(
            args={"bridge": "Cet espace est dédié à Vancelian."},
            confidence_min=0.5,
            current_topic={"product_code": "TOP_5"},
        )
        # 1 resume + 5 fixes = 6.
        assert len(decision.fallback_choices) == 6
        assert decision.fallback_choices[0].id == "resume_topic"
        assert "TOP_5" in decision.fallback_choices[0].label

    def test_no_bridge_returns_invalid_decision(self):
        decision = _parse_redirect_off_topic(
            args={"bridge": ""},
            confidence_min=0.5,
        )
        # Pas de bridge → pas de redirection valide.
        assert decision.redirect_bridge is None
        assert decision.confidence == 0.0
        assert decision.reasoning == "redirect_off_topic_no_bridge"


class TestAskClarificationHybrid:
    def test_tag_known_overrides_llm_options(self):
        # Le LLM envoie un tag valide → on utilise le catalogue,
        # ses prompt/options sont ignorés.
        decision = _parse_ask_clarification(
            args={
                "tag": "epargner",
                "prompt": "Texte LLM ignoré",
                "options": [
                    {"id": "default", "label": "Foo bar"},
                ],
            },
            confidence_min=0.5,
        )
        # Le prompt vient du catalogue.
        assert "épargne" in decision.reasoning.lower()
        # Les options sont celles du catalogue (3 entrées pour epargner).
        assert len(decision.fallback_choices) == 3
        ids = [c.id for c in decision.fallback_choices]
        assert "product" in ids
        assert "advisor" in ids
        # confidence sous le seuil pour déclencher le QCM.
        assert decision.confidence < 0.5

    def test_tag_unknown_falls_back_to_llm_options(self):
        decision = _parse_ask_clarification(
            args={
                "tag": "xxx_unknown_tag",
                "prompt": "Hello world",
                "options": [
                    {"id": "product", "label": "Une option produit"},
                    {"id": "advisor", "label": "Une option advisor"},
                ],
            },
            confidence_min=0.5,
        )
        assert decision.reasoning == "Hello world"
        assert len(decision.fallback_choices) == 2

    def test_no_tag_uses_llm_options(self):
        decision = _parse_ask_clarification(
            args={
                "prompt": "Quel angle veux-tu creuser ?",
                "options": [
                    {"id": "advisor", "label": "Conseil"},
                    {"id": "market", "label": "Marché"},
                ],
            },
            confidence_min=0.5,
        )
        assert "angle" in decision.reasoning
        assert len(decision.fallback_choices) == 2

    def test_tag_with_empty_options_in_args_still_uses_catalog(self):
        # Le LLM peut passer tag seul sans prompt/options — le catalogue
        # fournit tout.
        decision = _parse_ask_clarification(
            args={"tag": "performance", "prompt": "", "options": []},
            confidence_min=0.5,
        )
        assert len(decision.fallback_choices) >= 2
        assert "performance" in decision.reasoning.lower()

    def test_no_options_at_all_returns_invalid(self):
        decision = _parse_ask_clarification(
            args={"prompt": "hi", "options": []},
            confidence_min=0.5,
        )
        assert decision.reasoning == "ask_clarification_no_valid_options"


class TestRouterDecisionAttachesIntentClassification:
    """On vérifie que ``RouterDecision`` accepte bien le champ
    ``intent_classification`` ajouté en Lot 2b."""

    def test_decision_accepts_intent_classification(self):
        from services.assistance.agents.base import RouterDecision

        d = RouterDecision(
            agent_id="product",
            confidence=0.8,
            reasoning="ok",
            intent_classification={
                "primary_tag": "bundle_crypto",
                "family": "investir",
                "scope_level": 2,
            },
        )
        assert d.intent_classification is not None
        assert d.intent_classification["primary_tag"] == "bundle_crypto"
