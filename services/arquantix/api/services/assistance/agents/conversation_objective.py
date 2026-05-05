"""Conversation Objective Engine — Couche B du modèle « Cognitive Bot v4 ».

Référence : ``docs/arquantix/COGNITIVE_BOT.md`` § B. CONVERSATION
OBJECTIVE ENGINE.

──────────────────────────────────────────────────────────────────────
Pourquoi ce module existe
──────────────────────────────────────────────────────────────────────

Le ``CognitiveState`` (Lot 1) capture **où en est** le client. Mais
sans **objectif explicite**, chaque agent répond au sujet sans direction
stratégique : on traite un user paniqué exactement comme un user curieux,
ce qui produit des réponses « plates ».

Le ``ConversationObjective`` répond à cette question :

    > « Étant donné l'état émotionnel + le stage du client, quel est
    >   l'objectif business du tour, et quelle action concrète doit
    >   conclure la réponse ? »

Concrètement, on calcule pour chaque tour :

  * ``primary_goal``     ∈ {reassure, de_escalate, unblock, inform,
                            educate, convert}
  * ``next_best_action`` ∈ {give_proof, give_control, micro_step,
                            ask_question, recommend, call_to_action}
  * ``stop_pushing``     bool — interdit toute proposition produit /
                         CTA insistant. Activé sur FEAR + ANGER.
  * ``strategy_hint``    texte court (≤ 200 chars) injecté dans le
                         prompt agent pour guider le LLM.

Le tout est ensuite **injecté dans le system prompt** des agents experts
via ``render_objective_for_prompt``, sous la forme d'un bloc compact
``[OBJECTIVE] primary_goal=… | next_best_action=… | stop_pushing=…``.

──────────────────────────────────────────────────────────────────────
Stratégie de mapping
──────────────────────────────────────────────────────────────────────

V1 : table déterministe (config-as-code), pas de LLM additionnel. Pure
fonction du ``cognitive_state`` calculé au Lot 1. Latence nulle.

Règles (cf. § 5 du framework cognitif user — « mapping intention →
stratégie ») :

  | emotion      | défaut                                                | overrides
  |--------------|-------------------------------------------------------|---
  | FEAR         | reassure / give_proof / stop_pushing=True            | (toujours)
  | ANGER        | de_escalate / give_control / stop_pushing=True       | (toujours)
  | COMPLIANCE   | unblock / micro_step / stop_pushing=False            | (friction
  |              |                                                       |  = ennemi,
  |              |                                                       |  on pousse
  |              |                                                       |  doucement)
  | TRANSACTION  | inform / give_context / stop_pushing=False           | conversion →
  |              |                                                       |  upsell
  |              |                                                       |  doux
  | OPPORTUNITY  | educate / ask_question / stop_pushing=False          | recommendation /
  |              |                                                       |  conversion →
  |              |                                                       |  convert
  | CURIOSITY    | educate / ask_question / stop_pushing=False          | conversion →
  |              |                                                       |  convert
  | NEUTRAL      | inform / ask_question / stop_pushing=False           | conversion →
  |              |                                                       |  convert

L'invariant business le plus important est que **FEAR et ANGER
forcent ``stop_pushing=True``** : aucun produit ne doit être proposé
quand le client est en détresse émotionnelle. Cela protège la confiance
long-terme.

──────────────────────────────────────────────────────────────────────
Tests : ``tests/test_assistance_conversation_objective_unit.py``.
──────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

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
    KNOWN_STAGES,
    STAGE_CLARIFICATION,
    STAGE_CONVERSION,
    STAGE_DISCOVERY,
    STAGE_RECOMMENDATION,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Vocabulaire canonique
# ─────────────────────────────────────────────────────────────────────


# 6 primary_goals — alignés avec § C2 du framework cognitif user.
GOAL_REASSURE = "reassure"
GOAL_DE_ESCALATE = "de_escalate"
GOAL_UNBLOCK = "unblock"
GOAL_INFORM = "inform"
GOAL_EDUCATE = "educate"
GOAL_CONVERT = "convert"


KNOWN_GOALS: frozenset[str] = frozenset({
    GOAL_REASSURE,
    GOAL_DE_ESCALATE,
    GOAL_UNBLOCK,
    GOAL_INFORM,
    GOAL_EDUCATE,
    GOAL_CONVERT,
})


# 6 next_best_actions — formes concrètes que la réponse doit prendre.
ACTION_GIVE_PROOF = "give_proof"          # citer régulation, custody, infra
ACTION_GIVE_CONTROL = "give_control"      # rendre le contrôle au client (escalation, options)
ACTION_MICRO_STEP = "micro_step"          # une seule petite action concrète
ACTION_ASK_QUESTION = "ask_question"      # question pour collecter info / orienter
ACTION_RECOMMEND = "recommend"            # 1-2 produits / pistes adaptées
ACTION_CALL_TO_ACTION = "call_to_action"  # CTA explicite (deep-link, ouvrir, déposer)


KNOWN_ACTIONS: frozenset[str] = frozenset({
    ACTION_GIVE_PROOF,
    ACTION_GIVE_CONTROL,
    ACTION_MICRO_STEP,
    ACTION_ASK_QUESTION,
    ACTION_RECOMMEND,
    ACTION_CALL_TO_ACTION,
})


# ─────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ObjectiveEntry:
    """Entrée du catalogue de mapping (emotion[, stage]) → objectif.

    ``stop_pushing`` :
      * True  → l'agent expert NE DOIT PAS proposer de produit, CTA
                produit ou deep-link orienté conversion. Réservé aux
                états d'urgence émotionnelle (FEAR, ANGER).
      * False → push commercial autorisé (mais toujours ≤ 2 options).
    """

    primary_goal: str
    next_best_action: str
    stop_pushing: bool
    strategy_hint: str
    """Phrase courte (≤ 200 chars) injectée dans le prompt pour
    rappeler à l'agent expert la stratégie de réponse."""


@dataclass(frozen=True)
class ConversationObjective:
    """Snapshot final de l'objectif d'un tour, prêt à injecter dans le
    prompt et à persister dans ``assistance_agent_decisions``."""

    primary_goal: str
    next_best_action: str
    stop_pushing: bool
    strategy_hint: str
    source_emotion: str
    source_stage: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_goal": self.primary_goal,
            "next_best_action": self.next_best_action,
            "stop_pushing": bool(self.stop_pushing),
            "strategy_hint": self.strategy_hint,
            "source_emotion": self.source_emotion,
            "source_stage": self.source_stage,
        }

    @classmethod
    def from_dict(
        cls, data: Optional[dict[str, Any]]
    ) -> Optional["ConversationObjective"]:
        if not isinstance(data, dict):
            return None
        try:
            goal = str(data.get("primary_goal") or "")
            action = str(data.get("next_best_action") or "")
            if goal not in KNOWN_GOALS or action not in KNOWN_ACTIONS:
                return None
            return cls(
                primary_goal=goal,
                next_best_action=action,
                stop_pushing=bool(data.get("stop_pushing")),
                strategy_hint=str(data.get("strategy_hint") or "")[:300],
                source_emotion=str(data.get("source_emotion") or ""),
                source_stage=str(data.get("source_stage") or ""),
            )
        except Exception:  # noqa: BLE001
            return None


# ─────────────────────────────────────────────────────────────────────
# Catalogue défaut par émotion
# ─────────────────────────────────────────────────────────────────────


DEFAULT_BY_EMOTION: dict[str, ObjectiveEntry] = {
    EMOTIONAL_INTENT_FEAR: ObjectiveEntry(
        primary_goal=GOAL_REASSURE,
        next_best_action=ACTION_GIVE_PROOF,
        stop_pushing=True,
        strategy_hint=(
            "Client en peur. Réduis la complexité, donne des preuves "
            "factuelles (régulation, custody, infrastructure). NE "
            "PROPOSE AUCUN produit — restaure d'abord la confiance."
        ),
    ),
    EMOTIONAL_INTENT_ANGER: ObjectiveEntry(
        primary_goal=GOAL_DE_ESCALATE,
        next_best_action=ACTION_GIVE_CONTROL,
        stop_pushing=True,
        strategy_hint=(
            "Client en colère. Reconnais sa frustration EN PREMIER. "
            "Donne-lui le contrôle (option d'escalade, étapes claires "
            "pour résoudre). Évite toute justification longue ou "
            "promotion produit."
        ),
    ),
    EMOTIONAL_INTENT_COMPLIANCE: ObjectiveEntry(
        primary_goal=GOAL_UNBLOCK,
        next_best_action=ACTION_MICRO_STEP,
        stop_pushing=False,
        strategy_hint=(
            "Client bloqué côté KYC / opérations. La friction est "
            "l'ennemi : propose UNE seule micro-étape concrète et "
            "rappelle le bénéfice à débloquer ensuite."
        ),
    ),
    EMOTIONAL_INTENT_TRANSACTION: ObjectiveEntry(
        primary_goal=GOAL_INFORM,
        next_best_action=ACTION_ASK_QUESTION,
        stop_pushing=False,
        strategy_hint=(
            "Client veut consulter ses gains / historique. Highlight "
            "des chiffres factuels, contextualise (perf vs marché), "
            "puis pose UNE question pour optimiser."
        ),
    ),
    EMOTIONAL_INTENT_OPPORTUNITY: ObjectiveEntry(
        primary_goal=GOAL_EDUCATE,
        next_best_action=ACTION_ASK_QUESTION,
        stop_pushing=False,
        strategy_hint=(
            "Client cherche une opportunité. Simplifie, propose 1-2 "
            "options MAXIMUM (jamais 5+), crée une projection concrète "
            "puis demande sa préférence."
        ),
    ),
    EMOTIONAL_INTENT_CURIOSITY: ObjectiveEntry(
        primary_goal=GOAL_EDUCATE,
        next_best_action=ACTION_ASK_QUESTION,
        stop_pushing=False,
        strategy_hint=(
            "Client en découverte. Simplifie, ne donne JAMAIS 10 "
            "options, propose 1-2 angles concrets. Termine par une "
            "question qui qualifie son intérêt."
        ),
    ),
    EMOTIONAL_INTENT_NEUTRAL: ObjectiveEntry(
        primary_goal=GOAL_INFORM,
        next_best_action=ACTION_ASK_QUESTION,
        stop_pushing=False,
        strategy_hint=(
            "Client neutre. Réponds clairement à sa demande, puis pose "
            "une question ouverte pour comprendre son besoin profond."
        ),
    ),
}


# ─────────────────────────────────────────────────────────────────────
# Overrides par (émotion, stage) pour finesses contextuelles
# ─────────────────────────────────────────────────────────────────────


# Convention : seules les paires qui DIVERGENT du défaut sont listées.
OVERRIDE_BY_EMOTION_STAGE: dict[tuple[str, str], ObjectiveEntry] = {
    (EMOTIONAL_INTENT_OPPORTUNITY, STAGE_RECOMMENDATION): ObjectiveEntry(
        primary_goal=GOAL_CONVERT,
        next_best_action=ACTION_CALL_TO_ACTION,
        stop_pushing=False,
        strategy_hint=(
            "Client mûr (recommendation+OPPORTUNITY). Propose UN CTA "
            "explicite (deep-link instrument / bundle), pas plus."
        ),
    ),
    (EMOTIONAL_INTENT_OPPORTUNITY, STAGE_CONVERSION): ObjectiveEntry(
        primary_goal=GOAL_CONVERT,
        next_best_action=ACTION_CALL_TO_ACTION,
        stop_pushing=False,
        strategy_hint=(
            "Client en conversion + OPPORTUNITY. Confirme l'action "
            "ciblée et lève les dernières objections (frais, délais)."
        ),
    ),
    (EMOTIONAL_INTENT_CURIOSITY, STAGE_CONVERSION): ObjectiveEntry(
        primary_goal=GOAL_CONVERT,
        next_best_action=ACTION_CALL_TO_ACTION,
        stop_pushing=False,
        strategy_hint=(
            "Client curieux qui touche au bout du tunnel. Propose UN "
            "CTA précis (ouvrir le bundle / l'instrument déjà évoqué)."
        ),
    ),
    (EMOTIONAL_INTENT_NEUTRAL, STAGE_RECOMMENDATION): ObjectiveEntry(
        primary_goal=GOAL_EDUCATE,
        next_best_action=ACTION_RECOMMEND,
        stop_pushing=False,
        strategy_hint=(
            "Client neutre qui a reçu une recommandation. Recommande "
            "1-2 produits cohérents avec sa demande, sans pression."
        ),
    ),
    (EMOTIONAL_INTENT_NEUTRAL, STAGE_CONVERSION): ObjectiveEntry(
        primary_goal=GOAL_CONVERT,
        next_best_action=ACTION_CALL_TO_ACTION,
        stop_pushing=False,
        strategy_hint=(
            "Client neutre en phase de conversion. Confirme l'action "
            "concrète à venir avec un CTA explicite."
        ),
    ),
    (EMOTIONAL_INTENT_TRANSACTION, STAGE_CONVERSION): ObjectiveEntry(
        primary_goal=GOAL_INFORM,
        next_best_action=ACTION_CALL_TO_ACTION,
        stop_pushing=False,
        strategy_hint=(
            "Client transactionnel en conversion. Highlight les "
            "résultats (gain), propose UN CTA d'optimisation (ex. "
            "augmenter le coffre, diversifier)."
        ),
    ),
}


# ─────────────────────────────────────────────────────────────────────
# Compute principal
# ─────────────────────────────────────────────────────────────────────


def compute_objective(
    cognitive_state: Optional[CognitiveState],
) -> ConversationObjective:
    """Calcule le ``ConversationObjective`` à partir du
    ``CognitiveState`` du tour courant.

    Algorithme :
      1. Si ``cognitive_state`` est ``None`` → fallback NEUTRAL +
         DISCOVERY (objectif par défaut).
      2. Lookup ``OVERRIDE_BY_EMOTION_STAGE[(emotion, stage)]`` →
         si trouvé, utilisé directement.
      3. Sinon, lookup ``DEFAULT_BY_EMOTION[emotion]``.
      4. Fallback final : ``DEFAULT_BY_EMOTION[NEUTRAL]`` (sécurité).

    Cette fonction est **pure** (pas d'I/O, pas de LLM) — réversible
    et déterministe pour les tests.
    """
    if cognitive_state is None:
        emotion = EMOTIONAL_INTENT_NEUTRAL
        stage = STAGE_DISCOVERY
    else:
        emotion = (
            cognitive_state.emotional_intent
            if cognitive_state.emotional_intent in KNOWN_EMOTIONAL_INTENTS
            else EMOTIONAL_INTENT_NEUTRAL
        )
        stage = (
            cognitive_state.conversation_stage
            if cognitive_state.conversation_stage in KNOWN_STAGES
            else STAGE_DISCOVERY
        )

    entry = OVERRIDE_BY_EMOTION_STAGE.get((emotion, stage))
    if entry is None:
        entry = DEFAULT_BY_EMOTION.get(
            emotion, DEFAULT_BY_EMOTION[EMOTIONAL_INTENT_NEUTRAL]
        )

    return ConversationObjective(
        primary_goal=entry.primary_goal,
        next_best_action=entry.next_best_action,
        stop_pushing=entry.stop_pushing,
        strategy_hint=entry.strategy_hint,
        source_emotion=emotion,
        source_stage=stage,
    )


# ─────────────────────────────────────────────────────────────────────
# Rendu pour injection dans les prompts
# ─────────────────────────────────────────────────────────────────────


def render_objective_for_prompt(
    objective: Optional[ConversationObjective],
) -> Optional[str]:
    """Sérialise l'objectif en bloc compact prêt pour injection dans
    le system prompt d'un agent expert (ou du router).

    Format ::

        [OBJECTIVE] primary_goal = X | next_best_action = Y |
        stop_pushing = Z
        Hint: <strategy_hint>

    Retourne ``None`` si ``objective`` est ``None``. On rend toujours
    un bloc même pour le défaut NEUTRAL+DISCOVERY car les agents
    bénéficient toujours de la directive structurelle.
    """
    if objective is None:
        return None

    line1 = (
        "[OBJECTIVE] "
        + " | ".join(
            [
                f"primary_goal = {objective.primary_goal}",
                f"next_best_action = {objective.next_best_action}",
                f"stop_pushing = {'true' if objective.stop_pushing else 'false'}",
            ]
        )
    )

    if objective.strategy_hint:
        return f"{line1}\nHint: {objective.strategy_hint.strip()[:500]}"
    return line1


__all__ = [
    "ACTION_ASK_QUESTION",
    "ACTION_CALL_TO_ACTION",
    "ACTION_GIVE_CONTROL",
    "ACTION_GIVE_PROOF",
    "ACTION_MICRO_STEP",
    "ACTION_RECOMMEND",
    "ConversationObjective",
    "DEFAULT_BY_EMOTION",
    "GOAL_CONVERT",
    "GOAL_DE_ESCALATE",
    "GOAL_EDUCATE",
    "GOAL_INFORM",
    "GOAL_REASSURE",
    "GOAL_UNBLOCK",
    "KNOWN_ACTIONS",
    "KNOWN_GOALS",
    "ObjectiveEntry",
    "OVERRIDE_BY_EMOTION_STAGE",
    "compute_objective",
    "render_objective_for_prompt",
]
