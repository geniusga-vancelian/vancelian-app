"""Tool ``show_top_movers`` — agents **market** + **advisor**, autonomy **L0**.

Phase 2c.7 — Carte chat ``top_movers_crypto``. Pattern d'embed
**complémentaire** d'un message texte (le LLM commente la dynamique
du marché, le widget liste les actifs concernés, chacun cliquable
pour ouvrir la fiche instrument).

Usage typique :
  - User : *« quelle est la meilleure performance crypto sur 24h ? »*
  - Agent ``market`` : appelle ``show_top_movers(direction="gainers")``
    → carte UI listant 5 cryptos en hausse, chaque ligne ayant un
    deep-link ``view_instrument``.
  - User : *« qu'est-ce qui a le plus chuté ? »* →
    ``show_top_movers(direction="losers")``.
  - User : *« où est le volume aujourd'hui ? »* →
    ``show_top_movers(direction="volume")``.

Sources de données :
  - ``services.market_data.top_movers_repo.get_top_movers`` qui
    s'appuie sur les Binance providers actifs + les latest quotes.

Sécurité :
  - ``direction`` whitelistée stricte (gainers / losers / volume).
  - ``limit`` borné [1, 10].
  - Deep-links générés via ``action_cta_catalog.build_action`` avec
    ``instrument_id``.
  - Pas d'anti-tipping-off (données de marché publiques).

Cf. ``docs/arquantix/CHAT_EMBEDS_CATALOG.md`` § 2.5.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from database import MarketDataInstrument
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared.action_cta_catalog import (
    build_action,
)
from services.market_data.market_summary_repo import get_market_summaries
from services.market_data.quotes_repo import (
    get_latest_quotes_by_instrument_ids,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Whitelist
# ─────────────────────────────────────────────────────────────────────────


_VALID_DIRECTIONS: frozenset[str] = frozenset(
    {"gainers", "losers", "volume"}
)

_DEFAULT_LIMIT = 5
_MIN_LIMIT = 1
_MAX_LIMIT = 10

_BLOCK_TITLE: dict[str, str] = {
    "gainers": "Top hausses 24 h",
    "losers": "Top baisses 24 h",
    "volume": "Top volumes 24 h",
}


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "show_top_movers",
        "description": (
            "Affiche un BLOC LISTE DE CRYPTOS (top movers 24h) en "
            "complément de ta réponse texte. Chaque ligne montre logo, "
            "symbol, prix, variation 24h colorée. Ligne cliquable → "
            "fiche instrument.\n"
            "\n"
            "RÈGLE : tu peux ÉCRIRE EN PLUS un bref commentaire de "
            "marché au-dessus (1-3 phrases). Le widget porte les "
            "chiffres factuels.\n"
            "\n"
            "PARAM `direction` (obligatoire, whitelist stricte) :\n"
            "- `gainers` → top hausses 24h ;\n"
            "- `losers` → top baisses 24h ;\n"
            "- `volume` → top volumes 24h.\n"
            "\n"
            "PARAM `limit` (optionnel) : 1 à 10, défaut 5. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["gainers", "losers", "volume"],
                    "description": (
                        "Quel classement afficher. gainers = "
                        "performances positives 24h, losers = "
                        "négatives, volume = activité."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre de cryptos (1-10, défaut 5).",
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["direction"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "market",
}


# ─────────────────────────────────────────────────────────────────────────
# Implémentation
# ─────────────────────────────────────────────────────────────────────────


def execute(
    ctx: ToolContext,
    *,
    direction: Optional[str] = None,
    limit: Optional[int] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    raw_dir = (direction or "").strip().lower()
    if raw_dir not in _VALID_DIRECTIONS:
        return {
            "error": "invalid_direction",
            "supported_directions": sorted(_VALID_DIRECTIONS),
        }

    eff_limit = _DEFAULT_LIMIT
    if isinstance(limit, int):
        eff_limit = max(_MIN_LIMIT, min(_MAX_LIMIT, limit))

    try:
        all_summaries = _fetch_eligible_summaries(ctx.db)
    except Exception:  # noqa: BLE001
        logger.exception("show_top_movers.repo_error direction=%s", raw_dir)
        return {"error": "market_data_unavailable"}

    summaries = _sort_summaries(all_summaries, raw_dir, eff_limit)
    if not summaries:
        return {
            "direction": raw_dir,
            "items": [],
            "embed_emitted": False,
        }

    items: list[dict[str, Any]] = []
    for s in summaries:
        instrument_id = s.get("instrument_id")
        if instrument_id is None:
            continue
        # Symbol short-form pour affichage : on strip USDT/USDC suffixe
        # au cas où le repo renvoie le provider symbol.
        provider_symbol = (s.get("symbol") or "").strip().upper()
        short_symbol = _strip_quote_suffix(provider_symbol)

        price_eur = _safe_float(s.get("price_eur"))
        price_usd = _safe_float(s.get("price"))
        if price_eur is not None and price_eur > 0:
            display_currency = "EUR"
            display_price = price_eur
        elif price_usd is not None and price_usd > 0:
            display_currency = "USD"
            display_price = price_usd
        else:
            # Pas de prix exploitable → on saute la ligne.
            continue

        change_pct = _safe_float(s.get("change_24h_pct"))
        change_abs_raw = _safe_float(s.get("change_24h_abs"))
        if (
            display_currency == "EUR"
            and change_abs_raw is not None
            and price_usd
            and price_usd > 0
            and price_eur is not None
        ):
            change_abs = change_abs_raw * (price_eur / price_usd)
        else:
            change_abs = change_abs_raw

        logo_filename = s.get("logo_filename")
        logo_url: Optional[str] = None
        if isinstance(logo_filename, str) and logo_filename:
            logo_url = f"/media/{logo_filename}"

        action = build_action(
            "view_instrument", params={"instrument_id": str(instrument_id)}
        )

        items.append(
            {
                "instrument_id": int(instrument_id),
                "symbol": short_symbol or provider_symbol,
                "name": (s.get("name") or short_symbol or "").strip(),
                "logo_url": logo_url,
                "currency": display_currency,
                "price": float(display_price),
                "change_24h_abs": (
                    float(change_abs) if change_abs is not None else None
                ),
                "change_24h_pct": (
                    float(change_pct) if change_pct is not None else None
                ),
                "volume_24h": _safe_float(s.get("volume_24h")),
                "deep_link": action["deep_link"] if action else None,
            }
        )

    if not items:
        return {
            "direction": raw_dir,
            "items": [],
            "embed_emitted": False,
        }

    embed: dict[str, Any] = {
        "type": "top_movers_crypto",
        "direction": raw_dir,
        "title": _BLOCK_TITLE.get(raw_dir, "Top movers"),
        "items": items,
    }
    ctx.embeds_to_emit.append(embed)

    return {
        "direction": raw_dir,
        "count": len(items),
        "items": [
            {
                "symbol": it["symbol"],
                "price": it["price"],
                "currency": it["currency"],
                "change_24h_pct": it["change_24h_pct"],
            }
            for it in items
        ],
        "embed_emitted": True,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _fetch_eligible_summaries(db) -> list[dict[str, Any]]:
    """Charge tous les market summaries Binance actifs avec EUR.

    Mimique de ``top_movers_repo._eligible_binance_instrument_ids`` +
    ``get_market_summaries(include_eur=True)``. On préfère un appel
    direct ici plutôt que ``get_top_movers`` (qui ne passe pas
    ``include_eur=True``) pour avoir des prix en euros consommables
    par le widget chat.
    """
    rows = (
        db.query(MarketDataInstrument.id)
        .filter(
            MarketDataInstrument.provider == "binance",
            MarketDataInstrument.is_active == "true",
        )
        .all()
    )
    ids = [r[0] for r in rows]
    if not ids:
        return []
    quotes = get_latest_quotes_by_instrument_ids(db, ids)
    eligible_ids = [q.instrument_id for q in quotes]
    if not eligible_ids:
        return []
    return get_market_summaries(
        db, instrument_ids=eligible_ids, include_eur=True
    )


def _sort_summaries(
    summaries: list[dict[str, Any]],
    direction: str,
    limit: int,
) -> list[dict[str, Any]]:
    if direction == "gainers":
        with_pct = [
            s for s in summaries if s.get("change_24h_pct") is not None
        ]
        return sorted(
            with_pct, key=lambda s: s["change_24h_pct"], reverse=True
        )[:limit]
    if direction == "losers":
        with_pct = [
            s for s in summaries if s.get("change_24h_pct") is not None
        ]
        return sorted(with_pct, key=lambda s: s["change_24h_pct"])[:limit]
    # volume
    with_vol = [s for s in summaries if s.get("volume_24h") is not None]
    return sorted(
        with_vol, key=lambda s: s["volume_24h"], reverse=True
    )[:limit]


def _strip_quote_suffix(symbol: str) -> str:
    """``BTCUSDT`` → ``BTC`` ; idempotent pour les symbols déjà courts."""
    if not symbol:
        return ""
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)]
    return symbol


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["SPEC", "execute"]
