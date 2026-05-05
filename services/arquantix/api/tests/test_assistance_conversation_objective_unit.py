"""Tests unitaires pour ``conversation_objective.py`` (Cognitive Bot v4 — Lot 2).

Cf. ``docs/arquantix/COGNITIVE_BOT.md`` § B. CONVERSATION OBJECTIVE
ENGINE.

Vérifient :
  * Catalogue de mapping cohérent (toutes les emotions ont un défaut,
    tous les goals/actions sont valides).
  * ``compute_objective`` retourne les bons goals canoniques par
    émotion (FEAR → reassure, ANGER → de_escalate, etc.) avec
    ``stop_pushing=True`` sur les états d'urgence (FEAR + ANGER).
  * Les overrides ``(emotion, stage)`` prennent le pas sur le défaut.
  * ``render_objective_for_prompt`` produit le bon format avec les 3
    propriétés clés + le hint stratégique.
  * Robustesse : ``None``, dicts mal formés, émotions inconnues.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.cognitive_state import (
    CognitiveState,
    EMOTIONAL_INTENT_ANGER,
    EMOTIONAL_INTENT_COMPLIANCE,
    EMOTIONAL_INTENT_CURIOSITY,
    EMOTIONAL_INTENT_FEAR,
    EMOTIONAL_INTENT_NEUTRAL,
    EMOTIONAL_INTENT_OPPORTUNITY,
    EMOTIONAL_INTENT_TRANSACTION,
    KNOWN_EMOTIONAL_INTENTS,
    STAGE_CLARIFICATION,
    STAGE_CONVERSION,
    STAGE_DISCOVERY,
    STAGE_RECOMMENDATION,
)
from services.assistance.agents.conversation_objective import (
    ACTION_ASK_QUESTION,
    ACTION_CALL_TO_ACTION,
    ACTION_GIVE_CONTROL,
    ACTION_GIVE_PROOF,
    ACTION_MICRO_STEP,
    ACTION_RECOMMEND,
    ConversationObjective,
    DEFAULT_BY_EMOTION,
    GOAL_CONVERT,
    GOAL_DE_ESCALATE,
    GOAL_EDUCATE,
    GOAL_INFORM,
    GOAL_REASSURE,
    GOAL_UNBLOCK,
    KNOWN_ACTIONS,
    KNOWN_GOALS,
    OVERRIDE_BY_EMOTION_STAGE,
    compute_objective,
    render_objective_for_prompt,
)


# ─────────────────────────────────────────────────────────────────────
# Catalogue
# ─────────────────────────────────────────────────────────────────────


class TestCatalogShape:
    def test_all_emotions_have_default_entry(self):
        # Chaque emotion canonique (incl. NEUTRAL) doit avoir un défaut.
        for emotion in KNOWN_EMOTIONAL_INTENTS:
            assert emotion in DEFAULT_BY_EMOTION, (
                f"missing default for emotion={emotion}"
            )

    def test_default_entries_use_known_goals(self):
        for emotion, entry in DEFAULT_BY_EMOTION.items():
            assert entry.primary_goal in KNOWN_GOALS, (
                f"unknown goal {entry.primary_goal} for emotion={emotion}"
            )
            assert entry.next_best_action in KNOWN_ACTIONS, (
                f"unknown action {entry.next_best_action} for emotion={emotion}"
            )

    def test_overrides_use_known_goals(self):
        for key, entry in OVERRIDE_BY_EMOTION_STAGE.items():
            assert entry.primary_goal in KNOWN_GOALS
            assert entry.next_best_action in KNOWN_ACTIONS

    def test_fear_and_anger_force_stop_pushing(self):
        # Invariant business critique : on n'insiste JAMAIS sur un
        # client en FEAR / ANGER.
        assert DEFAULT_BY_EMOTION[EMOTIONAL_INTENT_FEAR].stop_pushing is True
        assert (
            DEFAULT_BY_EMOTION[EMOTIONAL_INTENT_ANGER].stop_pushing is True
        )

    def test_each_default_entry_has_strategy_hint(self):
        for emotion, entry in DEFAULT_BY_EMOTION.items():
            assert (
                entry.strategy_hint and len(entry.strategy_hint) >= 20
            ), f"empty / too short hint for emotion={emotion}"


# ─────────────────────────────────────────────────────────────────────
# compute_objective — défauts par emotion
# ─────────────────────────────────────────────────────────────────────


class TestComputeObjectiveDefaults:
    def test_fear_returns_reassure_give_proof_stop_pushing(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_FEAR,
            conversation_stage=STAGE_DISCOVERY,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_REASSURE
        assert obj.next_best_action == ACTION_GIVE_PROOF
        assert obj.stop_pushing is True
        assert obj.source_emotion == EMOTIONAL_INTENT_FEAR
        assert obj.source_stage == STAGE_DISCOVERY

    def test_anger_returns_de_escalate_give_control_stop_pushing(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_ANGER,
            conversation_stage=STAGE_RECOMMENDATION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_DE_ESCALATE
        assert obj.next_best_action == ACTION_GIVE_CONTROL
        assert obj.stop_pushing is True

    def test_compliance_returns_unblock_micro_step(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_COMPLIANCE,
            conversation_stage=STAGE_DISCOVERY,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_UNBLOCK
        assert obj.next_best_action == ACTION_MICRO_STEP
        assert obj.stop_pushing is False

    def test_transaction_default_is_inform_ask(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_TRANSACTION,
            conversation_stage=STAGE_DISCOVERY,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_INFORM
        assert obj.next_best_action == ACTION_ASK_QUESTION
        assert obj.stop_pushing is False

    def test_curiosity_returns_educate_ask_question(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_CURIOSITY,
            conversation_stage=STAGE_DISCOVERY,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_EDUCATE
        assert obj.next_best_action == ACTION_ASK_QUESTION

    def test_opportunity_default_is_educate_ask(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_OPPORTUNITY,
            conversation_stage=STAGE_DISCOVERY,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_EDUCATE
        assert obj.next_best_action == ACTION_ASK_QUESTION

    def test_neutral_default_is_inform_ask(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_NEUTRAL,
            conversation_stage=STAGE_DISCOVERY,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_INFORM
        assert obj.next_best_action == ACTION_ASK_QUESTION


# ─────────────────────────────────────────────────────────────────────
# compute_objective — overrides (emotion, stage)
# ─────────────────────────────────────────────────────────────────────


class TestComputeObjectiveOverrides:
    def test_opportunity_recommendation_pivot_to_convert(self):
        # Override clé : un client en OPPORTUNITY arrivé au stage
        # recommendation a déjà digéré une réponse → on doit pivoter
        # de educate vers convert.
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_OPPORTUNITY,
            conversation_stage=STAGE_RECOMMENDATION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_CONVERT
        assert obj.next_best_action == ACTION_CALL_TO_ACTION

    def test_opportunity_conversion_keeps_convert(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_OPPORTUNITY,
            conversation_stage=STAGE_CONVERSION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_CONVERT
        assert obj.next_best_action == ACTION_CALL_TO_ACTION

    def test_curiosity_conversion_pivot_to_convert(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_CURIOSITY,
            conversation_stage=STAGE_CONVERSION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_CONVERT
        assert obj.next_best_action == ACTION_CALL_TO_ACTION

    def test_curiosity_recommendation_keeps_educate_default(self):
        # Pas d'override → reste sur le défaut.
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_CURIOSITY,
            conversation_stage=STAGE_RECOMMENDATION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_EDUCATE
        assert obj.next_best_action == ACTION_ASK_QUESTION

    def test_neutral_recommendation_pivots_to_recommend(self):
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_NEUTRAL,
            conversation_stage=STAGE_RECOMMENDATION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_EDUCATE
        assert obj.next_best_action == ACTION_RECOMMEND

    def test_transaction_conversion_pivot_to_call_to_action(self):
        # Upsell doux : le client consulte ses gains, on lui propose
        # une étape d'optimisation.
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_TRANSACTION,
            conversation_stage=STAGE_CONVERSION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_INFORM
        assert obj.next_best_action == ACTION_CALL_TO_ACTION

    def test_fear_recommendation_keeps_reassure(self):
        # Le mantra : FEAR l'emporte sur n'importe quel stage. JAMAIS
        # de pivot vers convert, même en recommendation.
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_FEAR,
            conversation_stage=STAGE_RECOMMENDATION,
        )
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_REASSURE
        assert obj.next_best_action == ACTION_GIVE_PROOF
        assert obj.stop_pushing is True


# ─────────────────────────────────────────────────────────────────────
# compute_objective — robustesse
# ─────────────────────────────────────────────────────────────────────


class TestComputeObjectiveRobustness:
    def test_none_input_returns_neutral_default(self):
        obj = compute_objective(None)
        assert obj.primary_goal == GOAL_INFORM
        assert obj.next_best_action == ACTION_ASK_QUESTION
        assert obj.source_emotion == EMOTIONAL_INTENT_NEUTRAL
        assert obj.source_stage == STAGE_DISCOVERY

    def test_unknown_emotion_falls_back_neutral(self):
        # On crée un CognitiveState "sale" pour tester la robustesse.
        # En pratique CognitiveState normalize, mais le défensif ici
        # protège si quelqu'un construit l'objet à la main.
        state = CognitiveState()
        # Hack : remplace emotional_intent par une valeur inconnue.
        object.__setattr__(state, "emotional_intent", "weird_emotion")
        obj = compute_objective(state)
        assert obj.primary_goal == GOAL_INFORM  # = défaut NEUTRAL

    def test_unknown_stage_falls_back_discovery(self):
        state = CognitiveState(emotional_intent=EMOTIONAL_INTENT_FEAR)
        object.__setattr__(state, "conversation_stage", "weird_stage")
        obj = compute_objective(state)
        # FEAR + stage défaillant → garde le défaut FEAR.
        assert obj.primary_goal == GOAL_REASSURE
        assert obj.source_stage == STAGE_DISCOVERY


# ─────────────────────────────────────────────────────────────────────
# ConversationObjective — sérialisation
# ─────────────────────────────────────────────────────────────────────


class TestConversationObjectiveSerialization:
    def test_to_dict_round_trip(self):
        original = ConversationObjective(
            primary_goal=GOAL_REASSURE,
            next_best_action=ACTION_GIVE_PROOF,
            stop_pushing=True,
            strategy_hint="Client en peur, rassure d'abord",
            source_emotion=EMOTIONAL_INTENT_FEAR,
            source_stage=STAGE_DISCOVERY,
        )
        rebuilt = ConversationObjective.from_dict(original.to_dict())
        assert rebuilt is not None
        assert rebuilt.primary_goal == original.primary_goal
        assert rebuilt.next_best_action == original.next_best_action
        assert rebuilt.stop_pushing == original.stop_pushing
        assert rebuilt.strategy_hint == original.strategy_hint

    def test_from_dict_invalid_returns_none(self):
        assert ConversationObjective.from_dict(None) is None
        assert ConversationObjective.from_dict("not_a_dict") is None  # type: ignore[arg-type]
        assert ConversationObjective.from_dict({}) is None

    def test_from_dict_unknown_goal_returns_none(self):
        bad = {
            "primary_goal": "not_a_goal",
            "next_best_action": ACTION_GIVE_PROOF,
        }
        assert ConversationObjective.from_dict(bad) is None

    def test_from_dict_unknown_action_returns_none(self):
        bad = {
            "primary_goal": GOAL_REASSURE,
            "next_best_action": "not_an_action",
        }
        assert ConversationObjective.from_dict(bad) is None


# ─────────────────────────────────────────────────────────────────────
# render_objective_for_prompt
# ─────────────────────────────────────────────────────────────────────


class TestRenderObjectiveForPrompt:
    def test_none_input_returns_none(self):
        assert render_objective_for_prompt(None) is None

    def test_full_objective_renders_format(self):
        obj = ConversationObjective(
            primary_goal=GOAL_REASSURE,
            next_best_action=ACTION_GIVE_PROOF,
            stop_pushing=True,
            strategy_hint="Client en peur, rassure et donne des preuves",
            source_emotion=EMOTIONAL_INTENT_FEAR,
            source_stage=STAGE_DISCOVERY,
        )
        rendered = render_objective_for_prompt(obj)
        assert rendered is not None
        assert rendered.startswith("[OBJECTIVE]")
        assert "primary_goal = reassure" in rendered
        assert "next_best_action = give_proof" in rendered
        assert "stop_pushing = true" in rendered
        assert "Hint: Client en peur" in rendered

    def test_objective_without_hint_renders_only_first_line(self):
        obj = ConversationObjective(
            primary_goal=GOAL_INFORM,
            next_best_action=ACTION_ASK_QUESTION,
            stop_pushing=False,
            strategy_hint="",
            source_emotion=EMOTIONAL_INTENT_NEUTRAL,
            source_stage=STAGE_DISCOVERY,
        )
        rendered = render_objective_for_prompt(obj)
        assert rendered is not None
        assert "stop_pushing = false" in rendered
        assert "Hint:" not in rendered

    def test_neutral_default_renders_block(self):
        # Contrairement à `cognitive_state`, on rend TOUJOURS le bloc
        # objective (même neutre), car c'est une directive structurelle
        # utile à chaque tour.
        state = CognitiveState()
        obj = compute_objective(state)
        rendered = render_objective_for_prompt(obj)
        assert rendered is not None
        assert "primary_goal = inform" in rendered


# ─────────────────────────────────────────────────────────────────────
# Bout-à-bout : cognitive_state → objective
# ─────────────────────────────────────────────────────────────────────


class TestEndToEndCognitiveToObjective:
    def test_fear_user_in_recommendation_still_reassure(self):
        # Scénario réel : client en FEAR dans une conversation avancée
        # (recommendation). Le mapping doit toujours forcer reassure +
        # stop_pushing — le contexte conversationnel ne doit JAMAIS
        # surclasser l'urgence émotionnelle.
        state = CognitiveState(
            emotional_intent=EMOTIONAL_INTENT_FEAR,
            conversation_stage=STAGE_RECOMMENDATION,
            trust_level=0.30,
        )
        obj = compute_objective(state)
        assert obj.stop_pushing is True
        assert obj.primary_goal == GOAL_REASSURE

    def test_curiosity_progresses_through_funnel(self):
        # Scénario : client curieux qui avance dans le funnel.
        for stage, expected_goal, expected_action in [
            (STAGE_DISCOVERY, GOAL_EDUCATE, ACTION_ASK_QUESTION),
            (STAGE_CLARIFICATION, GOAL_EDUCATE, ACTION_ASK_QUESTION),
            (STAGE_RECOMMENDATION, GOAL_EDUCATE, ACTION_ASK_QUESTION),
            (STAGE_CONVERSION, GOAL_CONVERT, ACTION_CALL_TO_ACTION),
        ]:
            state = CognitiveState(
                emotional_intent=EMOTIONAL_INTENT_CURIOSITY,
                conversation_stage=stage,
            )
            obj = compute_objective(state)
            assert obj.primary_goal == expected_goal, f"stage={stage}"
            assert obj.next_best_action == expected_action, f"stage={stage}"
