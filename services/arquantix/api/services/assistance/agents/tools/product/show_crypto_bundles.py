"""Tool ``show_crypto_bundles`` — agent **product**, autonomy **L0**.

Phase 2 wiki — Carte chat ``crypto_bundles_card``. Pattern d'embed
**slidable** complémentaire d'un message texte du LLM, calqué sur
``show_instrument_card`` (carte instrument) mais ici **liste** des
bundles disponibles sous forme de slider horizontal (réplique exacte
côté chat de ``CryptoBundlesWidget`` côté markets/home).

Usage typique :
  - User : *« quels sont les bundles disponibles ? »*, *« je veux voir
    les crypto baskets »*, *« montre-moi les bundles que je peux
    prendre »*.
  - Agent ``product`` : appelle ``show_crypto_bundles()`` →
    embed ``crypto_bundles_card`` avec la liste des produits crypto
    bundle publics actifs (tap card = détail produit, bouton
    « Investir » = flow d'investissement).
  - Le LLM rédige *en plus* un texte court d'introduction en citant
    les bundles retournés (mais **n'invente** ni nom ni allocation).

Source de données :
  - ``services.portfolio_engine.products.catalog.CatalogService`` —
    réutilise tel quel le service qui sert l'endpoint
    ``GET /api/portfolio-engine/product-catalog?product_type=crypto_bundle``
    consommé côté Flutter par ``ProductCatalogApi.getCatalog``.
  - Filtre additionnel : on n'expose que les bundles ``is_public=True``,
    ``status=active`` et avec au moins une allocation (sinon la carte
    affiche du vide). Ces filtres sont déjà appliqués par
    ``get_public_catalog``.

Sécurité :
  - L0 read-only, idempotent, données publiques (catalogue produit).
  - Deep-links générés via ``action_cta_catalog.build_action`` :
    ``view_bundle_detail`` (tap card) + ``invest_bundle`` (bouton).
  - Pas de PII : seul le ``product_id`` (UUID) circule dans le
    deep-link, la résolution se fait côté Flutter (session JWT).

Cf. ``docs/arquantix/PRODUCT_AGENT.md`` (Phase 2 wiki — show_crypto_bundles).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared.action_cta_catalog import (
    build_action,
)
from services.portfolio_engine.products.catalog import CatalogService

logger = logging.getLogger(__name__)


# Le product_type filtré côté DB. Aligné avec ``ProductDefinition.product_type``
# pour les bundles crypto (cf. seed `pe_product_definitions`).
_PRODUCT_TYPE: str = "crypto_bundle"


# Plafond strict pour borner le payload (le slider mobile gère bien
# une dizaine de cards maxi avant de devenir confus). En réalité on
# en a 1-3 actifs publics aujourd'hui ; on garde une marge.
_MAX_BUNDLES: int = 8


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "show_crypto_bundles",
        "description": (
            "Affiche un SLIDER de cartes crypto bundles disponibles "
            "(catalogue Vancelian) en complément de ta réponse texte. "
            "Chaque carte montre nom + description courte + allocation + "
            "tap ouvre la fiche produit, bouton « Investir » lance le "
            "flow d'investissement. À utiliser **uniquement** quand le "
            "client veut voir PLUSIEURS bundles (« la liste des bundles », "
            "« quels paniers je peux prendre », « les bundles à dominante "
            "BTC », « découvrir les bundles »). **Si le client cible UN "
            "seul bundle nommé** (ex. « parle-moi du bundle TOP5 », « le "
            "Crypto Top 5 »), utilise plutôt `show_bundle_detail` qui "
            "affiche la fiche détaillée avec graphique. Tu peux ÉCRIRE "
            "EN PLUS un texte court d'introduction, mais **n'invente** "
            "ni nom ni allocation : cite uniquement ce que le tool "
            "renvoie. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Liste optionnelle de `product_code` (ex. "
                        "[\"TOP5\", \"ALT5\"]) pour filtrer la liste "
                        "des bundles à afficher. Si fourni, seuls ces "
                        "produits seront retournés. Sans paramètre = "
                        "tous les bundles publics actifs."
                    ),
                },
            },
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "product",
}


# ─────────────────────────────────────────────────────────────────────────
# Implémentation
# ─────────────────────────────────────────────────────────────────────────


def execute(
    ctx: ToolContext,
    *,
    product_codes: Optional[list[str]] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    try:
        catalog = CatalogService().get_public_catalog(
            ctx.db, product_type=_PRODUCT_TYPE
        )
    except Exception:  # noqa: BLE001 — defensive : DB indisponible
        logger.exception("show_crypto_bundles.catalog_error")
        return {"error": "catalog_unavailable"}

    if not catalog:
        # Cas réaliste en local si la DB n'a aucun bundle seed actif.
        # On retourne un payload exploitable par le LLM (qui pourra
        # signaler poliment au client) plutôt qu'une exception.
        logger.info("show_crypto_bundles.empty_catalog")
        return {
            "bundles_count": 0,
            "embed_emitted": False,
            "note": "no_active_bundle",
        }

    # Filtrage optionnel par `product_codes` (case-insensitive).
    # Le LLM peut filtrer après un premier appel pour ne montrer
    # qu'un sous-ensemble (ex. bundles à dominante BTC).
    requested_codes = _normalize_codes(product_codes)
    if requested_codes:
        filtered = [
            p
            for p in catalog
            if (p.product_code or "").strip().upper() in requested_codes
        ]
        if not filtered:
            logger.info(
                "show_crypto_bundles.no_match_after_filter "
                "requested=%s available=%s",
                sorted(requested_codes),
                [p.product_code for p in catalog],
            )
            return {
                "bundles_count": 0,
                "embed_emitted": False,
                "note": "no_match_for_product_codes",
                "available_product_codes": sorted(
                    {(p.product_code or "").upper() for p in catalog if p.product_code}
                ),
            }
        catalog = filtered

    items: list[dict[str, Any]] = []
    for product in catalog[:_MAX_BUNDLES]:
        bundle_id = str(product.id)
        allocations = [
            {
                "symbol": (alloc.asset_symbol or "").upper(),
                "instrument_name": alloc.instrument_name,
                "weight": float(alloc.target_weight or Decimal("0")),
            }
            for alloc in (product.allocations or [])
            if (alloc.asset_symbol or "").strip()
        ]

        view_action = build_action(
            "view_bundle_detail", params={"bundle_id": bundle_id}
        )
        invest_action = build_action(
            "invest_bundle", params={"bundle_id": bundle_id}
        )

        items.append(
            {
                "id": bundle_id,
                "product_code": product.product_code,
                "name": product.name,
                "description": (product.description or None),
                "risk_label": product.risk_label,
                "base_currency": product.base_currency,
                "entry_asset_default": product.entry_asset_default,
                "allocations": allocations,
                # Convention identique à ``instrument_detail_card`` :
                # `actions` est une liste d'`{kind, label, deep_link}`.
                # L'ordre est significatif côté Flutter (tap = view,
                # bouton = invest).
                "actions": [
                    a for a in (view_action, invest_action) if a is not None
                ],
            }
        )

    embed: dict[str, Any] = {
        "type": "crypto_bundles_card",
        "title": "Crypto Bundles",
        "bundles": items,
    }
    ctx.embeds_to_emit.append(embed)

    return {
        "bundles_count": len(items),
        "bundles": [
            {
                "id": b["id"],
                "name": b["name"],
                "product_code": b["product_code"],
                "allocations_summary": _summarize_allocations(b["allocations"]),
            }
            for b in items
        ],
        "embed_emitted": True,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _normalize_codes(raw: Optional[list[str]]) -> set[str]:
    """Normalise la liste de codes : strip, upper, drop empties."""
    if not raw:
        return set()
    return {
        s.strip().upper()
        for s in raw
        if isinstance(s, str) and s.strip()
    }


def _summarize_allocations(allocations: list[dict[str, Any]]) -> Optional[str]:
    """Résumé textuel court (pour le LLM) — ex. ``"50% BTC, 20% ETH, …"``.

    Le LLM peut utiliser ce résumé dans son texte d'accompagnement
    pour parler du bundle sans inventer. Retourne None si vide.
    """
    if not allocations:
        return None
    parts = []
    for a in allocations[:5]:
        sym = a.get("symbol") or "?"
        try:
            pct = round(float(a.get("weight") or 0) * 100)
        except (TypeError, ValueError):
            pct = 0
        if pct > 0:
            parts.append(f"{pct}% {sym}")
    return ", ".join(parts) if parts else None


__all__ = ["SPEC", "execute"]
