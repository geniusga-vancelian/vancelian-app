"""Tests unitaires pour ``cognitive_state.py`` (Cognitive Bot v4 — Lot 1).

Cf. ``docs/arquantix/COGNITIVE_BOT.md`` § A. STATE ENGINE.

Vérifient :
  * Cohérence du catalogue (ids canoniques, priorité ordre).
  * ``classify_emotional_intent`` détecte correctement par mot-clé FR/EN.
  * Le ``primary_intent`` respecte la priorité ANGER > FEAR > … > CURIOSITY.
  * ``infer_knowledge_level`` mappe correctement la mémoire long-terme.
  * ``compute_trust_level`` érode et regagne dans les bonnes plages,
    avec clamp [0, 1].
  * ``infer_conversation_stage`` infère discovery/clarification/
    recommendation/conversion à partir des signaux disponibles.
  * ``compute_cognitive_state`` orchestre le tout sans I/O.
  * ``render_cognitive_state_for_prompt`` ne pollue pas le prompt en
    état démarrage (NEUTRAL+DISCOVERY+0.5+LOW).
  * ``CognitiveState.from_dict`` est robuste aux dicts partiels / sales.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.cognitive_state import (
    CognitiveState,
    EMOTIONAL_INTENT_ANGER,
    EMOTIONAL_INTENT_CATALOG,
    EMOTIONAL_INTENT_COMPLIANCE,
    EMOTIONAL_INTENT_CURIOSITY,
    EMOTIONAL_INTENT_FEAR,
    EMOTIONAL_INTENT_NEUTRAL,
    EMOTIONAL_INTENT_OPPORTUNITY,
    EMOTIONAL_INTENT_PRIORITY,
    EMOTIONAL_INTENT_TRANSACTION,
    EMOTIONAL_INTENTS_BY_NAME,
    KNOWLEDGE_HIGH,
    KNOWLEDGE_LOW,
    KNOWLEDGE_MEDIUM,
    STAGE_CLARIFICATION,
    STAGE_CONVERSION,
    STAGE_DISCOVERY,
    STAGE_RECOMMENDATION,
    TRUST_DELTA_BY_EMOTION,
    classify_emotional_intent,
    compute_cognitive_state,
    compute_trust_level,
    infer_conversation_stage,
    infer_knowledge_level,
    render_cognitive_state_for_prompt,
)


# ─────────────────────────────────────────────────────────────────────
# Catalogue
# ─────────────────────────────────────────────────────────────────────


class TestCatalogShape:
    def test_unique_intent_ids(self):
        ids = [d.intent for d in EMOTIONAL_INTENT_CATALOG]
        assert len(ids) == len(set(ids)), f"duplicate emotional intents: {ids}"

    def test_priority_covers_all_non_neutral_intents(self):
        # NEUTRAL n'est pas dans le catalogue (c'est le fallback) ni
        # dans la priorité (jamais matché). Les 6 autres y sont.
        priority_set = set(EMOTIONAL_INTENT_PRIORITY)
        catalog_set = {d.intent for d in EMOTIONAL_INTENT_CATALOG}
        assert priority_set == catalog_set
        assert EMOTIONAL_INTENT_NEUTRAL not in priority_set

    def test_priority_is_anger_first_curiosity_last(self):
        # L'invariant business : sur multi-match, ANGER > FEAR > …
        # > CURIOSITY. C'est la base du framework cognitif (désescalade
        # absolue prioritaire sur exploration neutre-positive).
        assert EMOTIONAL_INTENT_PRIORITY[0] == EMOTIONAL_INTENT_ANGER
        assert EMOTIONAL_INTENT_PRIORITY[1] == EMOTIONAL_INTENT_FEAR
        assert EMOTIONAL_INTENT_PRIORITY[-1] == EMOTIONAL_INTENT_CURIOSITY

    def test_index_consistent(self):
        assert len(EMOTIONAL_INTENTS_BY_NAME) == len(EMOTIONAL_INTENT_CATALOG)

    def test_each_intent_has_at_least_one_keyword(self):
        for d in EMOTIONAL_INTENT_CATALOG:
            assert (
                d.keywords_fr or d.keywords_en
            ), f"intent {d.intent} has no keywords"

    def test_trust_delta_covers_all_emotions(self):
        # Tous les intents (incl. NEUTRAL) doivent avoir un delta connu.
        for intent in EMOTIONAL_INTENT_PRIORITY:
            assert intent in TRUST_DELTA_BY_EMOTION
        assert EMOTIONAL_INTENT_NEUTRAL in TRUST_DELTA_BY_EMOTION


# ─────────────────────────────────────────────────────────────────────
# classify_emotional_intent — détection unitaire
# ─────────────────────────────────────────────────────────────────────


class TestClassifyEmotionalIntentSingle:
    def test_empty_message_returns_neutral(self):
        result = classify_emotional_intent("")
        assert result.primary_intent == EMOTIONAL_INTENT_NEUTRAL
        assert result.matched_intents == ()

    def test_whitespace_message_returns_neutral(self):
        result = classify_emotional_intent("   \n  \t  ")
        assert result.primary_intent == EMOTIONAL_INTENT_NEUTRAL

    def test_neutral_message_returns_neutral(self):
        result = classify_emotional_intent("Salut")
        assert result.primary_intent == EMOTIONAL_INTENT_NEUTRAL

    def test_detects_fear_simple(self):
        result = classify_emotional_intent("J'ai peur de perdre mon argent")
        assert result.primary_intent == EMOTIONAL_INTENT_FEAR

    def test_detects_fear_english(self):
        result = classify_emotional_intent("I'm afraid I'll lose everything")
        assert result.primary_intent == EMOTIONAL_INTENT_FEAR

    def test_detects_anger_caps_french(self):
        result = classify_emotional_intent(
            "C'est inacceptable, ce service ne marche pas"
        )
        assert result.primary_intent == EMOTIONAL_INTENT_ANGER

    def test_detects_anger_demand_refund(self):
        result = classify_emotional_intent(
            "Je veux un remboursement immédiat"
        )
        assert result.primary_intent == EMOTIONAL_INTENT_ANGER

    def test_detects_curiosity_question(self):
        result = classify_emotional_intent(
            "Comment ça marche le Cloud Mining ?"
        )
        assert result.primary_intent == EMOTIONAL_INTENT_CURIOSITY

    def test_detects_curiosity_explain(self):
        result = classify_emotional_intent("Explique-moi le rendement")
        assert result.primary_intent == EMOTIONAL_INTENT_CURIOSITY

    def test_detects_compliance_kyc(self):
        result = classify_emotional_intent(
            "Mon KYC est bloqué depuis 3 jours, qu'est-ce qui se passe ?"
        )
        # Multi-match probable : COMPLIANCE (kyc, bloque) + CURIOSITY
        # (qu'est-ce que). Priorité COMPLIANCE > CURIOSITY.
        assert result.primary_intent == EMOTIONAL_INTENT_COMPLIANCE

    def test_detects_compliance_documents(self):
        result = classify_emotional_intent("Quels justificatifs envoyer ?")
        assert result.primary_intent == EMOTIONAL_INTENT_COMPLIANCE

    def test_detects_transaction_my_history(self):
        result = classify_emotional_intent(
            "Affiche-moi mon historique des opérations"
        )
        assert result.primary_intent == EMOTIONAL_INTENT_TRANSACTION

    def test_detects_transaction_my_balance(self):
        result = classify_emotional_intent("What is my balance ?")
        assert result.primary_intent == EMOTIONAL_INTENT_TRANSACTION

    def test_detects_opportunity_good_time(self):
        result = classify_emotional_intent(
            "C'est le bon moment pour acheter du Bitcoin ?"
        )
        # Match attendu : OPPORTUNITY ("le bon moment", "bon moment").
        # Le tag "bitcoin" appartient à intent_tags, pas à
        # emotional_intent — orthogonalité préservée.
        assert result.primary_intent == EMOTIONAL_INTENT_OPPORTUNITY

    def test_detects_opportunity_exclusive_offer(self):
        result = classify_emotional_intent(
            "Vous avez des offres exclusives en ce moment ?"
        )
        assert result.primary_intent == EMOTIONAL_INTENT_OPPORTUNITY


class TestClassifyEmotionalIntentNormalization:
    """Robustesse aux accents, casse, espaces, ponctuation."""

    def test_accents_are_ignored(self):
        result = classify_emotional_intent("J'ai peur de perdre")
        assert result.primary_intent == EMOTIONAL_INTENT_FEAR

    def test_uppercase_is_ignored(self):
        result = classify_emotional_intent("JE SUIS INQUIET")
        assert result.primary_intent == EMOTIONAL_INTENT_FEAR

    def test_mixed_punctuation(self):
        result = classify_emotional_intent("Peur, panique, doute !!!")
        assert result.primary_intent == EMOTIONAL_INTENT_FEAR

    def test_word_boundary_avoids_false_positive(self):
        # "doute" ne doit PAS matcher dans "redouter" ou "indouble"
        # (mais matche bien si délimité par non-alphanum). On teste ici
        # une phrase neutre qui contient le substring "peur" dans un
        # mot non-pertinent.
        result = classify_emotional_intent(
            "Le restaurant Stupeur a une bonne note"
        )
        # "peur" est en substring de "stupeur" → pas un token entier →
        # pas de match → NEUTRAL.
        assert result.primary_intent == EMOTIONAL_INTENT_NEUTRAL

    def test_apostrophe_french_works(self):
        # "j'ai peur" doit fonctionner même si l'utilisateur tape "j'ai
        # peur" avec une apostrophe typographique vs droite.
        result1 = classify_emotional_intent("j'ai peur")
        result2 = classify_emotional_intent("j’ai peur")  # apostrophe ’
        assert result1.primary_intent == EMOTIONAL_INTENT_FEAR
        assert result2.primary_intent == EMOTIONAL_INTENT_FEAR


class TestClassifyEmotionalIntentPriority:
    """Sur multi-match, vérifie l'ordre de priorité."""

    def test_anger_beats_fear(self):
        result = classify_emotional_intent(
            "C'est un scandale, j'ai peur de perdre tout"
        )
        assert EMOTIONAL_INTENT_ANGER in result.matched_intents
        assert EMOTIONAL_INTENT_FEAR in result.matched_intents
        assert result.primary_intent == EMOTIONAL_INTENT_ANGER

    def test_fear_beats_compliance(self):
        result = classify_emotional_intent(
            "Mon KYC est bloqué et j'ai peur de perdre mon argent"
        )
        assert EMOTIONAL_INTENT_FEAR in result.matched_intents
        assert EMOTIONAL_INTENT_COMPLIANCE in result.matched_intents
        assert result.primary_intent == EMOTIONAL_INTENT_FEAR

    def test_compliance_beats_curiosity(self):
        result = classify_emotional_intent(
            "Comment fonctionne la validation KYC ?"
        )
        # CURIOSITY ("comment", "fonctionne") + COMPLIANCE (kyc).
        # COMPLIANCE doit gagner.
        assert EMOTIONAL_INTENT_CURIOSITY in result.matched_intents
        assert EMOTIONAL_INTENT_COMPLIANCE in result.matched_intents
        assert result.primary_intent == EMOTIONAL_INTENT_COMPLIANCE

    def test_opportunity_beats_curiosity(self):
        result = classify_emotional_intent(
            "Comment savoir si c'est le bon moment ?"
        )
        # CURIOSITY (comment) + OPPORTUNITY (bon moment). Priorité OPP.
        assert result.primary_intent == EMOTIONAL_INTENT_OPPORTUNITY


# ─────────────────────────────────────────────────────────────────────
# infer_knowledge_level
# ─────────────────────────────────────────────────────────────────────


class TestInferKnowledgeLevel:
    def test_none_returns_low(self):
        assert infer_knowledge_level(None) == KNOWLEDGE_LOW

    def test_empty_dict_returns_low(self):
        assert infer_knowledge_level({}) == KNOWLEDGE_LOW

    def test_no_facts_key_returns_low(self):
        assert infer_knowledge_level({"updated_at": "2026-05-04"}) == KNOWLEDGE_LOW

    def test_empty_facts_returns_low(self):
        assert infer_knowledge_level({"facts": []}) == KNOWLEDGE_LOW

    def test_one_fact_returns_medium(self):
        assert (
            infer_knowledge_level(
                {"facts": [{"type": "investment_horizon", "value": "5y"}]}
            )
            == KNOWLEDGE_MEDIUM
        )

    def test_three_facts_returns_medium(self):
        assert (
            infer_knowledge_level({"facts": [{"v": i} for i in range(3)]})
            == KNOWLEDGE_MEDIUM
        )

    def test_four_facts_returns_high(self):
        assert (
            infer_knowledge_level({"facts": [{"v": i} for i in range(4)]})
            == KNOWLEDGE_HIGH
        )

    def test_many_facts_returns_high(self):
        assert (
            infer_knowledge_level({"facts": [{"v": i} for i in range(20)]})
            == KNOWLEDGE_HIGH
        )

    def test_invalid_input_returns_low(self):
        assert infer_knowledge_level("not_a_dict") == KNOWLEDGE_LOW
        assert infer_knowledge_level(42) == KNOWLEDGE_LOW


# ─────────────────────────────────────────────────────────────────────
# compute_trust_level
# ─────────────────────────────────────────────────────────────────────


class TestComputeTrustLevel:
    def test_none_prev_starts_at_default_neutral(self):
        # 0.5 + delta neutre (0.01) = 0.51
        result = compute_trust_level(
            prev_trust=None, emotional_intent=EMOTIONAL_INTENT_NEUTRAL
        )
        assert pytest.approx(result, abs=1e-3) == 0.51

    def test_anger_erodes_significantly(self):
        result = compute_trust_level(
            prev_trust=0.5, emotional_intent=EMOTIONAL_INTENT_ANGER
        )
        assert pytest.approx(result, abs=1e-3) == 0.35

    def test_fear_erodes_moderately(self):
        result = compute_trust_level(
            prev_trust=0.5, emotional_intent=EMOTIONAL_INTENT_FEAR
        )
        assert pytest.approx(result, abs=1e-3) == 0.40

    def test_compliance_erodes_lightly(self):
        result = compute_trust_level(
            prev_trust=0.5, emotional_intent=EMOTIONAL_INTENT_COMPLIANCE
        )
        assert pytest.approx(result, abs=1e-3) == 0.45

    def test_curiosity_gains_slowly(self):
        result = compute_trust_level(
            prev_trust=0.5, emotional_intent=EMOTIONAL_INTENT_CURIOSITY
        )
        assert pytest.approx(result, abs=1e-3) == 0.53

    def test_clamp_low(self):
        # ANGER prev=0.05 → 0.05 - 0.15 = -0.10 → clamp 0.0
        result = compute_trust_level(
            prev_trust=0.05, emotional_intent=EMOTIONAL_INTENT_ANGER
        )
        assert result == 0.0

    def test_clamp_high(self):
        # OPPORTUNITY prev=0.99 → 0.99 + 0.02 = 1.01 → clamp 1.0
        result = compute_trust_level(
            prev_trust=0.99, emotional_intent=EMOTIONAL_INTENT_OPPORTUNITY
        )
        assert result == 1.0

    def test_invalid_prev_falls_back_to_default(self):
        # str invalide → fallback 0.5
        result = compute_trust_level(
            prev_trust="oops",  # type: ignore[arg-type]
            emotional_intent=EMOTIONAL_INTENT_NEUTRAL,
        )
        assert pytest.approx(result, abs=1e-3) == 0.51

    def test_unknown_emotion_uses_neutral_delta(self):
        result = compute_trust_level(
            prev_trust=0.5, emotional_intent="not_an_emotion"
        )
        # Fallback delta neutre.
        assert pytest.approx(result, abs=1e-3) == 0.51


# ─────────────────────────────────────────────────────────────────────
# infer_conversation_stage
# ─────────────────────────────────────────────────────────────────────


class TestInferConversationStage:
    def test_first_turn_returns_discovery(self):
        result = infer_conversation_stage(
            prev_state=None,
            intent_classification=None,
            last_router_decision_kind=None,
            recent_turns=[],
        )
        assert result == STAGE_DISCOVERY

    def test_first_turn_with_one_user_message_still_discovery(self):
        result = infer_conversation_stage(
            prev_state=None,
            intent_classification=None,
            last_router_decision_kind=None,
            recent_turns=[{"role": "user", "content": "salut"}],
        )
        assert result == STAGE_DISCOVERY

    def test_ask_clarification_returns_clarification(self):
        prev = CognitiveState(conversation_stage=STAGE_DISCOVERY)
        result = infer_conversation_stage(
            prev_state=prev,
            intent_classification={"preferred_agent": "advisor"},
            last_router_decision_kind="ask_clarification",
            recent_turns=[
                {"role": "user", "content": "j'aimerais épargner"},
                {"role": "assistant", "content": "qcm"},
            ],
        )
        assert result == STAGE_CLARIFICATION

    def test_route_to_expert_returns_recommendation(self):
        prev = CognitiveState(conversation_stage=STAGE_CLARIFICATION)
        result = infer_conversation_stage(
            prev_state=prev,
            intent_classification={"preferred_agent": "advisor"},
            last_router_decision_kind="route_to",
            recent_turns=[
                {"role": "user", "content": "préparer ma retraite"},
                {"role": "assistant", "content": "Je te conseille..."},
            ],
        )
        assert result == STAGE_RECOMMENDATION

    def test_route_to_compliance_keeps_prev_stage(self):
        # `compliance` n'est pas dans expert_agents (c'est de
        # l'opérationnel, pas de la recommandation business).
        prev = CognitiveState(conversation_stage=STAGE_DISCOVERY)
        result = infer_conversation_stage(
            prev_state=prev,
            intent_classification={"preferred_agent": "compliance"},
            last_router_decision_kind="route_to",
            recent_turns=[
                {"role": "user", "content": "où est mon retrait"},
                {"role": "assistant", "content": "le retrait est..."},
            ],
        )
        # On reste sur le stage précédent (continuité).
        assert result == STAGE_DISCOVERY

    def test_deep_link_in_recent_turns_returns_conversion(self):
        prev = CognitiveState(conversation_stage=STAGE_RECOMMENDATION)
        result = infer_conversation_stage(
            prev_state=prev,
            intent_classification={"preferred_agent": "product"},
            last_router_decision_kind="route_to",
            recent_turns=[
                {"role": "user", "content": "ouvre-moi le bundle TOP5"},
                {
                    "role": "assistant",
                    "content": "Voici TOP5 [/products/CRYPTO_TOP5]",
                },
            ],
        )
        assert result == STAGE_CONVERSION

    def test_instruments_deep_link_also_conversion(self):
        prev = CognitiveState(conversation_stage=STAGE_RECOMMENDATION)
        result = infer_conversation_stage(
            prev_state=prev,
            intent_classification={"preferred_agent": "product"},
            last_router_decision_kind="route_to",
            recent_turns=[
                {
                    "role": "assistant",
                    "content": "Voir BTC: /instruments/BTC",
                },
            ],
        )
        assert result == STAGE_CONVERSION

    def test_redirect_off_topic_keeps_prev_stage(self):
        # Off-topic → on garde le stage précédent (le client a juste
        # divergé, il revient probablement sur le sujet ensuite).
        prev = CognitiveState(conversation_stage=STAGE_RECOMMENDATION)
        result = infer_conversation_stage(
            prev_state=prev,
            intent_classification=None,
            last_router_decision_kind="redirect_off_topic",
            recent_turns=[
                {"role": "user", "content": "c'est quoi la météo"},
            ],
        )
        assert result == STAGE_RECOMMENDATION


# ─────────────────────────────────────────────────────────────────────
# compute_cognitive_state — orchestration
# ─────────────────────────────────────────────────────────────────────


class TestComputeCognitiveStateEndToEnd:
    def test_first_turn_neutral_message(self):
        state = compute_cognitive_state(
            user_message="bonjour",
            prev_state=None,
            intent_classification=None,
            last_router_decision_kind=None,
            client_long_memory=None,
            recent_turns=[],
        )
        assert state.emotional_intent == EMOTIONAL_INTENT_NEUTRAL
        assert state.conversation_stage == STAGE_DISCOVERY
        assert pytest.approx(state.trust_level, abs=1e-3) == 0.51
        assert state.knowledge_level == KNOWLEDGE_LOW

    def test_first_turn_fear_message_erodes_trust(self):
        state = compute_cognitive_state(
            user_message="J'ai peur de perdre mes économies",
            prev_state=None,
            intent_classification=None,
            last_router_decision_kind=None,
            client_long_memory=None,
            recent_turns=[],
        )
        assert state.emotional_intent == EMOTIONAL_INTENT_FEAR
        assert pytest.approx(state.trust_level, abs=1e-3) == 0.40
        assert state.conversation_stage == STAGE_DISCOVERY

    def test_continuity_anger_then_neutral(self):
        # Tour 1 : ANGER → trust 0.35
        state1 = compute_cognitive_state(
            user_message="C'est un scandale inacceptable",
            prev_state=None,
            intent_classification=None,
            last_router_decision_kind=None,
            client_long_memory=None,
            recent_turns=[],
        )
        assert state1.emotional_intent == EMOTIONAL_INTENT_ANGER
        assert pytest.approx(state1.trust_level, abs=1e-3) == 0.35

        # Tour 2 : message NEUTRAL après désescalade → trust 0.36
        state2 = compute_cognitive_state(
            user_message="ok merci",
            prev_state=state1,
            intent_classification={"preferred_agent": "compliance"},
            last_router_decision_kind="route_to",
            client_long_memory=None,
            recent_turns=[
                {"role": "user", "content": "scandale inacceptable"},
                {"role": "assistant", "content": "je comprends..."},
            ],
        )
        assert state2.emotional_intent == EMOTIONAL_INTENT_NEUTRAL
        assert pytest.approx(state2.trust_level, abs=1e-3) == 0.36

    def test_knowledge_level_uses_long_memory(self):
        client_mem = {
            "facts": [
                {"type": "investment_horizon", "value": "5y"},
                {"type": "risk_appetite", "value": "moderate"},
                {"type": "monthly_savings", "value": "500"},
                {"type": "goal", "value": "retraite"},
            ]
        }
        state = compute_cognitive_state(
            user_message="ok",
            prev_state=None,
            intent_classification=None,
            last_router_decision_kind=None,
            client_long_memory=client_mem,
            recent_turns=[],
        )
        assert state.knowledge_level == KNOWLEDGE_HIGH

    def test_recommendation_stage_from_route_to_advisor(self):
        prev = CognitiveState(conversation_stage=STAGE_CLARIFICATION)
        state = compute_cognitive_state(
            user_message="préparer ma retraite",
            prev_state=prev,
            intent_classification={"preferred_agent": "advisor"},
            last_router_decision_kind="route_to",
            client_long_memory=None,
            recent_turns=[
                {"role": "user", "content": "ma retraite"},
                {"role": "assistant", "content": "ok je conseille..."},
            ],
        )
        assert state.conversation_stage == STAGE_RECOMMENDATION


# ─────────────────────────────────────────────────────────────────────
# render_cognitive_state_for_prompt
# ─────────────────────────────────────────────────────────────────────


class TestRenderCognitiveStateForPrompt:
    def test_none_input_returns_none(self):
        assert render_cognitive_state_for_prompt(None) is None

    def test_neutral_default_returns_none_no_pollution(self):
        # État démarrage strict : NEUTRAL + DISCOVERY + ~0.5 + LOW →
        # on ne pollue pas le prompt.
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_NEUTRAL,
            conversation_stage=STAGE_DISCOVERY,
            trust_level=0.5,
            knowledge_level=KNOWLEDGE_LOW,
        )
        assert render_cognitive_state_for_prompt(state) is None

    def test_fear_state_renders_block(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_FEAR,
            conversation_stage=STAGE_RECOMMENDATION,
            trust_level=0.30,
            knowledge_level=KNOWLEDGE_MEDIUM,
        )
        rendered = render_cognitive_state_for_prompt(state)
        assert rendered is not None
        assert rendered.startswith("[COGNITIVE STATE]")
        assert "emotional_intent = fear" in rendered
        assert "conversation_stage = recommendation" in rendered
        assert "trust_level = 0.30" in rendered
        assert "knowledge_level = medium" in rendered

    def test_high_knowledge_renders_block_even_if_neutral(self):
        # Si le seul élément non-default est knowledge_level=HIGH, on
        # rend quand même (info utile pour les agents).
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_NEUTRAL,
            conversation_stage=STAGE_DISCOVERY,
            trust_level=0.5,
            knowledge_level=KNOWLEDGE_HIGH,
        )
        rendered = render_cognitive_state_for_prompt(state)
        assert rendered is not None
        assert "knowledge_level = high" in rendered


# ─────────────────────────────────────────────────────────────────────
# CognitiveState.from_dict — robustesse
# ─────────────────────────────────────────────────────────────────────


class TestCognitiveStateFromDict:
    def test_full_dict(self):
        state = CognitiveState.from_dict(
            {
                "emotional_intent": "fear",
                "conversation_stage": "recommendation",
                "trust_level": 0.42,
                "knowledge_level": "high",
                "matched_emotional_intents": ["fear", "curiosity"],
            }
        )
        assert state.emotional_intent == EMOTIONAL_INTENT_FEAR
        assert state.conversation_stage == STAGE_RECOMMENDATION
        assert state.trust_level == 0.42
        assert state.knowledge_level == KNOWLEDGE_HIGH
        assert state.matched_emotional_intents == ("fear", "curiosity")

    def test_partial_dict_uses_defaults(self):
        state = CognitiveState.from_dict({"emotional_intent": "anger"})
        assert state.emotional_intent == EMOTIONAL_INTENT_ANGER
        assert state.conversation_stage == STAGE_DISCOVERY
        assert state.trust_level == 0.5
        assert state.knowledge_level == KNOWLEDGE_LOW

    def test_invalid_emotion_falls_back_neutral(self):
        state = CognitiveState.from_dict({"emotional_intent": "unknown_x"})
        assert state.emotional_intent == EMOTIONAL_INTENT_NEUTRAL

    def test_invalid_stage_falls_back_discovery(self):
        state = CognitiveState.from_dict({"conversation_stage": "weird"})
        assert state.conversation_stage == STAGE_DISCOVERY

    def test_trust_level_clamped(self):
        assert CognitiveState.from_dict({"trust_level": 5.0}).trust_level == 1.0
        assert (
            CognitiveState.from_dict({"trust_level": -1.0}).trust_level == 0.0
        )

    def test_invalid_trust_level_str_falls_back(self):
        state = CognitiveState.from_dict({"trust_level": "not_a_number"})
        assert state.trust_level == 0.5

    def test_none_input_returns_neutral_default(self):
        state = CognitiveState.from_dict(None)
        assert state.emotional_intent == EMOTIONAL_INTENT_NEUTRAL
        assert state.conversation_stage == STAGE_DISCOVERY
        assert state.trust_level == 0.5
        assert state.knowledge_level == KNOWLEDGE_LOW

    def test_to_dict_round_trip(self):
        original = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_FEAR,
            conversation_stage=STAGE_RECOMMENDATION,
            trust_level=0.42,
            knowledge_level=KNOWLEDGE_MEDIUM,
            matched_emotional_intents=("fear",),
        )
        as_dict = original.to_dict()
        rebuilt = CognitiveState.from_dict(as_dict)
        assert rebuilt.emotional_intent == original.emotional_intent
        assert rebuilt.conversation_stage == original.conversation_stage
        assert rebuilt.trust_level == original.trust_level
        assert rebuilt.knowledge_level == original.knowledge_level
        assert rebuilt.matched_emotional_intents == original.matched_emotional_intents
