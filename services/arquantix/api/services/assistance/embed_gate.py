"""Filtrage des embeds UI selon état cognitif / objectif (expérience client).

Réduit la surcharge visuelle quand ``stop_pushing`` ou forte détresse
(``fear``, ``anger``) : enlève uniquement les widgets **discovery / promo**
— jamais une confirmation transactionnelle, un flux CAL ou une donnée perso
critique.

Classification (audit produit) :
  DISCOVERY_WIDGET | PROMO_WIDGET → **retirables** sous stress ;
  INFO_WIDGET | TRANSACTIONAL_WIDGET | CONFIRMATION_WIDGET | SECURITY_WIDGET
  → **protégés**.
Les types inconnus sont traités comme **INFO_WIDGET** (principe de précaution).
"""

from __future__ import annotations

import logging
from typing import Any, Final, Optional

logger = logging.getLogger(__name__)

# ── Taxonomie officielle (compatible audit / future UI BO) ─────────────

EMBED_WIDGET_CLASS_DISCOVERY: Final[str] = "DISCOVERY_WIDGET"
EMBED_WIDGET_CLASS_PROMO: Final[str] = "PROMO_WIDGET"
EMBED_WIDGET_CLASS_INFO: Final[str] = "INFO_WIDGET"
EMBED_WIDGET_CLASS_TRANSACTIONAL: Final[str] = "TRANSACTIONAL_WIDGET"
EMBED_WIDGET_CLASS_CONFIRMATION: Final[str] = "CONFIRMATION_WIDGET"
EMBED_WIDGET_CLASS_SECURITY: Final[str] = "SECURITY_WIDGET"

_EMBED_TYPE_CLASSIFICATION: dict[str, str] = {
    # Exploration produit / catalogue riches (strip sous détresse).
    "bundle_detail_card": EMBED_WIDGET_CLASS_DISCOVERY,
    "crypto_bundles_card": EMBED_WIDGET_CLASS_DISCOVERY,
    "instrument_detail_card": EMBED_WIDGET_CLASS_DISCOVERY,
    # Promotions / contenus éditoriaux.
    "featured_articles_list": EMBED_WIDGET_CLASS_PROMO,
    # Information marché (pas CTA d'achat direct sur un instrument montré).
    "top_movers_crypto": EMBED_WIDGET_CLASS_INFO,
    # CAL — ne jamais confondre avec du marketing.
    "invest_source_account_list": EMBED_WIDGET_CLASS_TRANSACTIONAL,
    "invest_confirmation_draft": EMBED_WIDGET_CLASS_CONFIRMATION,
    "action_widget": EMBED_WIDGET_CLASS_TRANSACTIONAL,
    # Ops / données personnelles.
    "transaction_detail": EMBED_WIDGET_CLASS_TRANSACTIONAL,
    "portfolio_allocation_donut": EMBED_WIDGET_CLASS_INFO,
}

HIGH_DISTRESS_EMOTIONS: frozenset[str] = frozenset(
    {"fear", "anger"},
)


def classify_embed_widget(embed_type: str) -> str:
    """Retourne la classe fonctionnelle d'un embed (cf. constantes ``EMBED_WIDGET_CLASS_*``)."""
    key = str(embed_type or "").strip()
    return _EMBED_TYPE_CLASSIFICATION.get(key, EMBED_WIDGET_CLASS_INFO)


def distress_may_strip_embed(embed_type: str) -> bool:
    """True seulement pour discovery / promo (filtrage sous stress autorisé)."""
    cls = classify_embed_widget(embed_type)
    return cls in (
        EMBED_WIDGET_CLASS_DISCOVERY,
        EMBED_WIDGET_CLASS_PROMO,
    )


# Dérivé --- nom historique utilisé dans tests / observabilité.
DISTRESS_STRIPPABLE_EMBED_TYPES: frozenset[str] = frozenset(
    k for k, v in _EMBED_TYPE_CLASSIFICATION.items() if distress_may_strip_embed(k)
)


PROMOTIONAL_EMBED_TYPES: frozenset[str] = DISTRESS_STRIPPABLE_EMBED_TYPES


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
            if distress_may_strip_embed(t):
                stripped += 1
                continue
            filtered.append(e)
        out = filtered
        if stripped:
            logger.info(
                "assistance.embed_gate.stripped_discovery_or_promo count=%s "
                "emo=%s stop_push=%s",
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
        # Priorité : garder d'abord données transactionnelles / confirmation.
        protected_first = frozenset(
            {
                "invest_confirmation_draft",
                "action_widget",
                "invest_source_account_list",
                "transaction_detail",
            },
        )

        def _rank(e: dict[str, Any]) -> tuple[int, str]:
            t = str(e.get("type") or "")
            if t == "invest_confirmation_draft":
                return (0, t)
            if t == "action_widget":
                return (1, t)
            if t == "transaction_detail":
                return (2, t)
            if t == "invest_source_account_list":
                return (3, t)
            if t == "portfolio_allocation_donut":
                return (4, t)
            if t in protected_first:
                return (5, t)
            return (6, t)

        out = sorted(out, key=_rank)[:max_total]
        logger.debug(
            "assistance.embed_gate.capped_after_stress len=%s cap=%s",
            len(embeds or []),
            max_total,
        )

    return out


__all__ = [
    "classify_embed_widget",
    "distress_may_strip_embed",
    "DISTRESS_STRIPPABLE_EMBED_TYPES",
    "EMBED_WIDGET_CLASS_CONFIRMATION",
    "EMBED_WIDGET_CLASS_DISCOVERY",
    "EMBED_WIDGET_CLASS_INFO",
    "EMBED_WIDGET_CLASS_PROMO",
    "EMBED_WIDGET_CLASS_SECURITY",
    "EMBED_WIDGET_CLASS_TRANSACTIONAL",
    "gate_embeds_for_ui_experience",
    "PROMOTIONAL_EMBED_TYPES",
]
