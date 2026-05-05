"""Tool ``show_bundle_detail`` — agent **product**, autonomy **L0**.

Phase 2 wiki — Carte chat ``bundle_detail_card``. Pattern d'embed
auto-suffisant **complémentaire** d'un message texte du LLM, calqué
sur ``show_instrument_card`` mais pour UN bundle spécifique (vs
``show_crypto_bundles`` qui affiche un slider de plusieurs bundles).

Réplique la **partie haute** de la page détail bundle
(``BundleInstrumentDetailHero``) dans une bulle chat :

- Tag « Crypto Bundle »
- Avatar empilé des allocations (``BundleAllocationAvatarStack``)
- Titre + description
- Performance row (alimentée côté Flutter par
  ``BundlePerformanceChartModule.onHeroMetricsChanged``)
- Chart de performance bord-à-bord (réutilise
  ``BundlePerformanceChartModule`` en mode
  ``embedInstrumentHero: true`` + ``chartContainerWidth``)
- CTAs « Voir détail » + « Investir »

Usage typique :
  - User : *« parle-moi du bundle TOP5 »*, *« le Crypto Top 5 »*,
    *« qu'est-ce que le bundle ALT5 »*.
  - Agent ``product`` : appelle
    ``show_bundle_detail(product_code="TOP5")`` (ou ``bundle_id``)
    → embed ``bundle_detail_card`` avec la fiche détaillée.
  - Le LLM rédige *en plus* un texte court d'introduction (qui peut
    citer les chiffres retournés mais ne **doit jamais inventer** un
    nom, une allocation ou une performance).

Source de données :
  - ``CatalogService.get_public_catalog(product_type='crypto_bundle')``
    — réutilise tel quel le service backend (0 modif catalog).
  - Le chart de performance lui-même est chargé côté Flutter via
    ``BundlePerformanceChartModule._load`` (endpoint
    ``/api/portfolio-engine/products/{id}/chart-history``) — pas
    besoin de pousser le payload chart depuis ce tool.

Sécurité :
  - L0 read-only, idempotent, données publiques (catalogue produit).
  - Deep-links générés via ``action_cta_catalog.build_action`` :
    ``view_bundle_detail`` (tap card / bouton « Voir ») +
    ``invest_bundle`` (bouton « Investir »).
  - Pas de PII : seul le ``product_id`` (UUID) circule dans le
    deep-link.

Cf. ``docs/arquantix/PRODUCT_AGENT.md`` (Phase 2 wiki —
show_bundle_detail).
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


# Identique à ``show_crypto_bundles`` — alignement product_type DB.
_PRODUCT_TYPE: str = "crypto_bundle"


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "show_bundle_detail",
        "description": (
            "Affiche la FICHE DÉTAILLÉE d'UN bundle Vancelian "
            "(graphique de performance + allocations + CTAs Voir/"
            "Investir) en complément de ta réponse texte. À utiliser "
            "quand le client cible UN bundle nommé : « parle-moi du "
            "bundle TOP5 », « le Crypto Top 5 », « qu'est-ce que le "
            "bundle ALT5 ». **N'utilise PAS** ce tool si le client "
            "veut voir plusieurs bundles à la fois (utilise alors "
            "`show_crypto_bundles`). Tu peux ÉCRIRE EN PLUS un texte "
            "explicatif court, mais **n'invente** ni nom ni allocation "
            "ni performance — cite uniquement ce que retourne le tool. "
            "Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_code": {
                    "type": "string",
                    "description": (
                        "Code produit canonique (ex. \"TOP5\", \"ALT5\"). "
                        "Insensible à la casse. Utilise ce paramètre en "
                        "priorité — c'est ce que le client a en tête."
                    ),
                },
                "bundle_id": {
                    "type": "string",
                    "description": (
                        "UUID du bundle (`pe_product_definitions.id`). À "
                        "utiliser en alternative au `product_code` si tu "
                        "as l'ID exact (ex. récupéré d'un précédent "
                        "appel `show_crypto_bundles`)."
                    ),
                },
            },
            # Au moins un des deux doit être fourni — validation runtime
            # dans `execute`. On ne pose pas de `required` strict pour
            # laisser le LLM passer l'un ou l'autre.
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
    product_code: Optional[str] = None,
    bundle_id: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    code = (product_code or "").strip().upper()
    bid = (bundle_id or "").strip()
    if not code and not bid:
        return {
            "error": "missing_identifier",
            "hint": "fournis product_code (ex. 'TOP5') ou bundle_id (UUID)",
        }

    try:
        catalog = CatalogService().get_public_catalog(
            ctx.db, product_type=_PRODUCT_TYPE
        )
    except Exception:  # noqa: BLE001 — defensive : DB indisponible
        logger.exception("show_bundle_detail.catalog_error")
        return {"error": "catalog_unavailable"}

    if not catalog:
        logger.info("show_bundle_detail.empty_catalog")
        return {
            "error": "no_active_bundle",
            "embed_emitted": False,
        }

    # Match priorité : product_code (string upper) > bundle_id (UUID).
    target = None
    if code:
        for p in catalog:
            if (p.product_code or "").strip().upper() == code:
                target = p
                break
    if target is None and bid:
        for p in catalog:
            if str(p.id) == bid:
                target = p
                break

    if target is None:
        available_codes = sorted(
            {(p.product_code or "").upper() for p in catalog if p.product_code}
        )
        logger.info(
            "show_bundle_detail.not_found code=%r id=%r available=%s",
            code,
            bid,
            available_codes,
        )
        return {
            "error": "bundle_not_found",
            "available_product_codes": available_codes,
        }

    bundle_id_str = str(target.id)
    allocations = [
        {
            "symbol": (alloc.asset_symbol or "").upper(),
            "instrument_name": alloc.instrument_name,
            "weight": float(alloc.target_weight or Decimal("0")),
        }
        for alloc in (target.allocations or [])
        if (alloc.asset_symbol or "").strip()
    ]

    view_action = build_action(
        "view_bundle_detail", params={"bundle_id": bundle_id_str}
    )
    invest_action = build_action(
        "invest_bundle", params={"bundle_id": bundle_id_str}
    )

    embed: dict[str, Any] = {
        "type": "bundle_detail_card",
        "id": bundle_id_str,
        "product_code": target.product_code,
        "name": target.name,
        "description": (target.description or None),
        "risk_label": target.risk_label,
        "base_currency": target.base_currency,
        "entry_asset_default": target.entry_asset_default,
        "allocations": allocations,
        "actions": [a for a in (view_action, invest_action) if a is not None],
    }
    ctx.embeds_to_emit.append(embed)

    return {
        "bundle": {
            "id": bundle_id_str,
            "product_code": target.product_code,
            "name": target.name,
            "risk_label": target.risk_label,
            "allocations_summary": _summarize_allocations(allocations),
        },
        "embed_emitted": True,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _summarize_allocations(allocations: list[dict[str, Any]]) -> Optional[str]:
    """Résumé textuel court (pour le LLM) — ex. ``"60% BTC, 40% ETH"``."""
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
