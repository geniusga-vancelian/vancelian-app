"""Filtrage des embeds UI selon état cognitif / objectif (expérience client).

Réduit la surcharge visuelle quand ``stop_pushing`` ou forte détresse
(``fear``, ``anger``) : enlève widgets « exploration / promo » avant SSE + DB.

Types d’embed traités comme **promotionnels / exploration**
(produit, marchés « découverte ») ; les embeddings **personnels / ops**
(transaction, donut allocation utilisateur typiquement conservés — max plafonné).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Types produits « cartes riches » ou veille ludique susceptible de choquer en colère/peur.
PROMOTIONAL_EMBED_TYPES: frozenset[str] = frozenset(
    {
        "bundle_detail_card",
        "crypto_bundles_card",
        "instrument_detail_card",
        "featured_articles_list",
        "top_movers_crypto",
        "invest_source_account_list",
        "invest_confirmation_draft",
    }
)

HIGH_DISTRESS_EMOTIONS: frozenset[str] = frozenset(
    {"fear", "anger"},
)


def gate_embeds_for_ui_experience(
    embeds: Optional[list[dict[str, Any]]],
    *,
    cognitive_state: Optional[dict[str, Any]],
    objective: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retourne une **copie** filtrée (jamais None — liste peut être vide)."""
    seq = list(embeds or [])
    if not seq:
        return []

    stress = False
    if isinstance(objective, dict) and bool(objective.get("stop_pushing")):
        stress = True

    emo = ""
    if isinstance(cognitive_state, dict):
        emo = str(cognitive_state.get("emotional_intent") or "").strip().lower()
    high_distress = emo in HIGH_DISTRESS_EMOTIONS
    if high_distress:
        stress = True

    out = seq
    if stress:
        out = [e for e in out if isinstance(e, dict)]
        filtered = []
        stripped = 0
        for e in out:
            t = str(e.get("type") or "").strip()
            if t in PROMOTIONAL_EMBED_TYPES:
                stripped += 1
                continue
            filtered.append(e)
        out = filtered
        if stripped:
            logger.info(
                "assistance.embed_gate.stripped_promo count=%s emo=%s stop_push=%s",
                stripped,
                emo or "-",
                bool(isinstance(objective, dict) and objective.get("stop_pushing")),
            )

    max_total = len(out)
    if high_distress:
        max_total = min(max_total, 1)
    elif isinstance(objective, dict) and bool(objective.get("stop_pushing")):
        max_total = min(max_total, 2)

    if len(out) > max_total:
        # Priorité lexicographique stable : garder ops (transaction…) en premier
        def _rank(e: dict[str, Any]) -> tuple[int, str]:
            t = str(e.get("type") or "")
            if t == "transaction_detail":
                return (0, t)
            if t == "portfolio_allocation_donut":
                return (1, t)
            return (2, t)

        out = sorted(out, key=_rank)[:max_total]
        logger.debug(
            "assistance.embed_gate.capped_after_stress len=%s cap=%s",
            len(embeds or []),
            max_total,
        )

    return out


__all__ = [
    "PROMOTIONAL_EMBED_TYPES",
    "gate_embeds_for_ui_experience",
]
