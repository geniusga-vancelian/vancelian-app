"""Helpers read-only pour lire l'état cognitif depuis ``ToolContext``.

Cognitive Bot v4 — Lot 2 « Cognitive State injecté dans chaque
sub-agent » (2026-05-06).

Ce module offre une API stable et défensive pour les tools qui
souhaitent lire ``ctx.cognitive_state`` et ``ctx.objective`` sans
dupliquer le boilerplate ``isinstance(...) + dict.get(...) +
fallback``. Aucune logique métier ici : juste de la **lecture
typée**.

──────────────────────────────────────────────────────────────────────
Pourquoi des helpers et pas un accès direct ?
──────────────────────────────────────────────────────────────────────

* ``ctx.cognitive_state`` est un ``Optional[dict]`` (cf. design Lot 2,
  cf. ``contracts.py``). Si chaque tool gère lui-même les ``None`` +
  les clés manquantes + les valeurs corrompues, on duplique la
  défensivité 30× et on risque des incohérences (un tool qui assume
  ``"neutral"`` en fallback, un autre ``"unknown"``, …).
* On veut que les tools puissent réagir à ``stop_pushing=True``
  sans importer toute la chaîne ``cognitive_state.py`` /
  ``conversation_objective.py`` (cycles d'imports potentiels,
  surtout côté ``tools/product/`` et ``tools/compliance/``).
* On veut une **batterie de helpers testable** (cf.
  ``tests/test_assistance_cognitive_context_unit.py``).

──────────────────────────────────────────────────────────────────────
Convention de fallback
──────────────────────────────────────────────────────────────────────

Quand l'état n'est pas disponible (``None``, dict vide, valeur
inconnue), tous les helpers renvoient un défaut **NEUTRAL /
discovery / stop_pushing=False**. C'est cohérent avec la
philosophie du framework cognitif : sans signal contraire, on traite
le client comme neutre et on n'interdit rien.

──────────────────────────────────────────────────────────────────────
Sécurité & invariants
──────────────────────────────────────────────────────────────────────

* **Read-only** : aucun helper ne mute ``ctx``.
* **Pure** : pas d'I/O, pas de DB, pas de LLM.
* **Pas d'exception** : une entrée mal formée renvoie le défaut.
* **Pas de cycle d'import** : on importe ``ToolContext`` localement
  via ``TYPE_CHECKING`` pour éviter d'imposer une dépendance
  circulaire à ``contracts.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from services.assistance.agents.tools.contracts import ToolContext


# ─────────────────────────────────────────────────────────────────────
# Constantes — alignées sur cognitive_state.py / conversation_objective.py
# ─────────────────────────────────────────────────────────────────────


# Émotions connues (cf. ``cognitive_state.KNOWN_EMOTIONAL_INTENTS``).
# Recopiées ici pour éviter le cycle d'import ; un test garantit la
# cohérence (cf. ``test_constants_aligned_with_cognitive_state``).
_KNOWN_EMOTIONS: frozenset[str] = frozenset({
    "fear",
    "anger",
    "curiosity",
    "compliance",
    "transaction",
    "opportunity",
    "neutral",
})

_KNOWN_STAGES: frozenset[str] = frozenset({
    "discovery",
    "clarification",
    "recommendation",
    "conversion",
})

_KNOWN_GOALS: frozenset[str] = frozenset({
    "reassure",
    "de_escalate",
    "unblock",
    "inform",
    "educate",
    "convert",
})

_KNOWN_ACTIONS: frozenset[str] = frozenset({
    "give_proof",
    "give_control",
    "micro_step",
    "ask_question",
    "recommend",
    "call_to_action",
})


# Émotions qui imposent un comportement défensif côté tool (pas de
# push commercial, pas de CTA insistant, ton apaisant). Aligné sur
# ``conversation_objective.DEFAULT_BY_EMOTION[FEAR/ANGER].stop_pushing``.
URGENT_EMOTIONS: frozenset[str] = frozenset({"fear", "anger"})


# ─────────────────────────────────────────────────────────────────────
# Lecture du cognitive_state
# ─────────────────────────────────────────────────────────────────────


def get_emotional_intent(ctx: "ToolContext") -> str:
    """Retourne l'émotion dominante du tour.

    Defaults à ``"neutral"`` si l'état est absent ou invalide.
    Garanti d'être dans ``_KNOWN_EMOTIONS``.
    """
    cog = ctx.cognitive_state
    if not isinstance(cog, dict):
        return "neutral"
    raw = cog.get("emotional_intent")
    if not isinstance(raw, str):
        return "neutral"
    val = raw.strip().lower()
    return val if val in _KNOWN_EMOTIONS else "neutral"


def get_conversation_stage(ctx: "ToolContext") -> str:
    """Retourne le stage courant. Defaults ``"discovery"``."""
    cog = ctx.cognitive_state
    if not isinstance(cog, dict):
        return "discovery"
    raw = cog.get("conversation_stage")
    if not isinstance(raw, str):
        return "discovery"
    val = raw.strip().lower()
    return val if val in _KNOWN_STAGES else "discovery"


def get_trust_level(ctx: "ToolContext") -> float:
    """Retourne le ``trust_level`` ∈ [0, 1]. Defaults à ``0.5``.

    Robustes aux strings, ``None``, et valeurs hors bornes
    (clamping silencieux).
    """
    cog = ctx.cognitive_state
    if not isinstance(cog, dict):
        return 0.5
    raw = cog.get("trust_level")
    try:
        val = float(raw) if raw is not None else 0.5
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, val))


def get_knowledge_level(ctx: "ToolContext") -> str:
    """Retourne ``low`` | ``medium`` | ``high``. Defaults ``low``."""
    cog = ctx.cognitive_state
    if not isinstance(cog, dict):
        return "low"
    raw = cog.get("knowledge_level")
    if not isinstance(raw, str):
        return "low"
    val = raw.strip().lower()
    return val if val in {"low", "medium", "high"} else "low"


# ─────────────────────────────────────────────────────────────────────
# Lecture de l'objective
# ─────────────────────────────────────────────────────────────────────


def get_primary_goal(ctx: "ToolContext") -> str:
    """Retourne le ``primary_goal`` du tour. Defaults ``"inform"``
    (le défaut NEUTRAL côté ``conversation_objective.py``)."""
    obj = ctx.objective
    if not isinstance(obj, dict):
        return "inform"
    raw = obj.get("primary_goal")
    if not isinstance(raw, str):
        return "inform"
    val = raw.strip().lower()
    return val if val in _KNOWN_GOALS else "inform"


def get_next_best_action(ctx: "ToolContext") -> str:
    """Retourne la ``next_best_action``. Defaults ``"ask_question"``."""
    obj = ctx.objective
    if not isinstance(obj, dict):
        return "ask_question"
    raw = obj.get("next_best_action")
    if not isinstance(raw, str):
        return "ask_question"
    val = raw.strip().lower()
    return val if val in _KNOWN_ACTIONS else "ask_question"


def should_stop_pushing(ctx: "ToolContext") -> bool:
    """``True`` si le bot doit arrêter toute proposition produit / CTA
    insistant (cas FEAR + ANGER, cf. framework cognitif).

    Stratégie de fallback (par ordre de priorité) :

      1. ``ctx.objective["stop_pushing"]`` si explicite (priorité au
         calcul aval qui peut surclasser le défaut).
      2. Sinon, ``True`` si l'``emotional_intent`` est dans
         ``URGENT_EMOTIONS``.
      3. ``False`` par défaut.
    """
    obj = ctx.objective
    if isinstance(obj, dict) and "stop_pushing" in obj:
        return bool(obj.get("stop_pushing"))
    return get_emotional_intent(ctx) in URGENT_EMOTIONS


def get_strategy_hint(ctx: "ToolContext") -> Optional[str]:
    """Retourne le ``strategy_hint`` brut (≤ 300 chars) si présent."""
    obj = ctx.objective
    if not isinstance(obj, dict):
        return None
    raw = obj.get("strategy_hint")
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    return val[:300] if val else None


# ─────────────────────────────────────────────────────────────────────
# Helper de plus haut niveau — snapshot compact pour log/diagnostic
# ─────────────────────────────────────────────────────────────────────


def cognitive_snapshot(ctx: "ToolContext") -> dict[str, Any]:
    """Snapshot compact de l'état cognitif + objectif pour log/audit.

    Format stable, JSON-friendly, utilisable dans un retour de tool
    pour exposer ce que le tool a "vu" du client (utile pour debug
    en cas de réponse qui surprend l'utilisateur final).

    Exemple :

    ::

        return {
            "matches": [...],
            "_cognitive": cognitive_snapshot(ctx),
        }
    """
    return {
        "emotional_intent": get_emotional_intent(ctx),
        "conversation_stage": get_conversation_stage(ctx),
        "trust_level": round(get_trust_level(ctx), 3),
        "knowledge_level": get_knowledge_level(ctx),
        "primary_goal": get_primary_goal(ctx),
        "next_best_action": get_next_best_action(ctx),
        "stop_pushing": should_stop_pushing(ctx),
    }


__all__ = [
    "URGENT_EMOTIONS",
    "cognitive_snapshot",
    "get_conversation_stage",
    "get_emotional_intent",
    "get_knowledge_level",
    "get_next_best_action",
    "get_primary_goal",
    "get_strategy_hint",
    "get_trust_level",
    "should_stop_pushing",
]
