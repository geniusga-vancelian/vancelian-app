"""Tool ``show_instrument_card`` — agents **product** + **advisor**, autonomy **L0**.

Phase 2c.6 — Carte chat ``instrument_detail_card``. Pattern d'embed
auto-suffisant **complémentaire** d'un message texte du LLM (différent
de ``read_transaction_detail`` ou ``stats_portfolio_allocation`` où le
LLM doit se taire).

Usage typique :
  - User : *« peux-tu me parler du Bitcoin ? »*
  - Agent ``product`` : appelle ``show_instrument_card(symbol="BTC")``
    → carte UI avec prix, perf 24h, sparkline et boutons Acheter / Vendre.
  - Le LLM rédige *en plus* une réponse pédagogique sur Bitcoin (peut
    citer les chiffres retournés par le tool).

Sources de données (toutes publiques) :
  - ``MarketDataInstrument`` pour `name`, `logo_filename`,
    `provider_symbol`.
  - ``services.market_data.market_summary_repo.get_market_summaries``
    pour `price`, `price_eur`, `change_24h_abs/pct`, `sparkline_24h`
    (24h de bars 5m, jusqu'à 288 points). Live fallback Binance déjà
    géré côté repo.

Sécurité :
  - Whitelist statique de symbols supportés (cf. ``_ALLOWED_SYMBOLS``)
    pour borner ce que le LLM peut requêter.
  - Deep-links générés via ``action_cta_catalog.build_action`` (jamais
    de format string libre).
  - Pas d'anti-tipping-off (données de marché publiques).

Cf. ``docs/arquantix/PRODUCT_AGENT.md`` (à venir : Phase 2c.6).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import or_

from database import MarketDataInstrument
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared.action_cta_catalog import (
    build_action,
)
from services.market_data.market_summary_repo import get_market_summaries

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Whitelist des symbols supportés Phase 2c.6
# ─────────────────────────────────────────────────────────────────────────
#
# Aligné avec ``crypto_detail_screen.dart::assetFromSlug`` côté Flutter.
# Le LLM passera par exemple "BTC", "ETH"... La résolution accepte aussi
# le `provider_symbol` (ex. "BTCUSDT") par souplesse.
_ALLOWED_SYMBOLS: frozenset[str] = frozenset(
    {
        "BTC", "ETH", "USDT", "USDC", "SOL", "XRP",
        "ADA", "AVAX", "DOT", "DOGE", "TRX",
    }
)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "show_instrument_card",
        "description": (
            "Affiche une CARTE INSTRUMENT en complément de ta réponse texte : "
            "logo + nom + prix actuel + variation 24h + mini-sparkline + "
            "boutons Acheter / Vendre. À utiliser quand le client pose "
            "une question sur un instrument crypto précis (« parle-moi "
            "du Bitcoin », « comment va l'Ether ? », « infos sur Solana »). "
            "Tu peux ÉCRIRE EN PLUS un texte explicatif (la carte montre "
            "les chiffres factuels, ton texte apporte le contexte). "
            "**N'invente jamais** un montant — cite uniquement les "
            "chiffres retournés par ce tool. "
            "Symbols supportés : BTC, ETH, USDT, USDC, SOL, XRP, ADA, "
            "AVAX, DOT, DOGE, TRX. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": (
                        "Symbol court de l'instrument (ex. \"BTC\", \"ETH\", "
                        "\"SOL\"). Insensible à la casse. Tu peux aussi "
                        "passer le provider symbol Binance (ex. \"BTCUSDT\")."
                    ),
                },
            },
            "required": ["symbol"],
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
    symbol: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    raw_symbol = (symbol or "").strip().upper()
    if not raw_symbol:
        return {"error": "missing_symbol"}

    short_symbol = _normalize_short_symbol(raw_symbol)
    if short_symbol not in _ALLOWED_SYMBOLS:
        logger.info(
            "show_instrument_card.unsupported symbol=%r short=%r",
            raw_symbol,
            short_symbol,
        )
        return {
            "error": "unsupported_instrument",
            "supported_symbols": sorted(_ALLOWED_SYMBOLS),
        }

    inst = _resolve_instrument(ctx.db, raw_symbol, short_symbol)
    if inst is None:
        return {"error": "unsupported_instrument"}

    try:
        summaries = get_market_summaries(
            ctx.db,
            instrument_ids=[inst.id],
            include_eur=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "show_instrument_card.market_data_error symbol=%r",
            short_symbol,
        )
        return {"error": "market_data_unavailable"}

    if not summaries:
        return {"error": "market_data_unavailable"}

    summary = summaries[0]
    price_usd = _safe_float(summary.get("price"))
    price_eur = _safe_float(summary.get("price_eur"))

    # Affichage en EUR si dispo, sinon fallback USD (raw price).
    if price_eur is not None and price_eur > 0:
        currency = "EUR"
        display_price = price_eur
    elif price_usd is not None and price_usd > 0:
        currency = "USD"
        display_price = price_usd
    else:
        return {"error": "market_data_unavailable"}

    # Variation 24h : `change_24h_abs/pct` du repo sont calculés en
    # USD (devise raw). Si on affiche en EUR, on doit reconvertir l'abs
    # à la même proportion. Pour la variation `pct`, c'est invariant
    # (un % reste un %). Pour `abs`, on multiplie par (price_eur /
    # price_usd) pour obtenir la même variation en EUR.
    change_pct = _safe_float(summary.get("change_24h_pct"))
    raw_change_abs = _safe_float(summary.get("change_24h_abs"))
    if (
        currency == "EUR"
        and raw_change_abs is not None
        and price_usd
        and price_usd > 0
        and price_eur is not None
    ):
        change_abs = raw_change_abs * (price_eur / price_usd)
    else:
        change_abs = raw_change_abs

    sparkline = [
        float(p)
        for p in (summary.get("sparkline_24h") or [])
        if isinstance(p, (int, float)) and p > 0
    ]
    # Si on affiche en EUR, on convertit la sparkline (proportionnel
    # à la conversion USD→EUR). Approximation : on suppose que la
    # paire EUR/USD n'a pas bougé sur 24h (acceptable pour l'usage
    # affichage).
    if (
        currency == "EUR"
        and sparkline
        and price_usd
        and price_usd > 0
        and price_eur is not None
    ):
        eur_factor = price_eur / price_usd
        sparkline = [p * eur_factor for p in sparkline]

    logo_url = (
        f"/media/{inst.logo_filename}"
        if getattr(inst, "logo_filename", None)
        else None
    )

    buy_action = build_action(
        "buy_instrument", params={"instrument_id": str(inst.id)}
    )
    sell_action = build_action(
        "sell_instrument", params={"instrument_id": str(inst.id)}
    )

    name = (inst.name or "").strip() or short_symbol

    embed: dict[str, Any] = {
        "type": "instrument_detail_card",
        "instrument_id": inst.id,
        "symbol": short_symbol,
        "name": name,
        "logo_url": logo_url,
        "currency": currency,
        "price": float(display_price),
        "change_24h_abs": (
            float(change_abs) if change_abs is not None else None
        ),
        "change_24h_pct": (
            float(change_pct) if change_pct is not None else None
        ),
        "sparkline_24h": sparkline,
        "actions": [a for a in (buy_action, sell_action) if a is not None],
    }
    ctx.embeds_to_emit.append(embed)

    return {
        "instrument": {"symbol": short_symbol, "name": name},
        "price": {
            "value": float(display_price),
            "currency": currency,
        },
        "performance_24h": {
            "abs": (float(change_abs) if change_abs is not None else None),
            "pct": (float(change_pct) if change_pct is not None else None),
            "currency": currency,
        },
        "embed_emitted": True,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _normalize_short_symbol(raw: str) -> str:
    """Renvoie le symbol court (ex. ``BTC``) à partir de ``BTC`` ou ``BTCUSDT``.

    Convention Binance : ``<BASE><QUOTE>`` où QUOTE ∈ {USDT, USDC, BUSD,
    USD}. On strip uniquement ces quotes connus, pour éviter d'amputer
    accidentellement un symbol comme « DOT » → « DO ».
    """
    if not raw:
        return ""
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if raw.endswith(quote) and len(raw) > len(quote):
            return raw[: -len(quote)]
    return raw


def _resolve_instrument(
    db,
    raw_symbol: str,
    short_symbol: str,
) -> Optional[MarketDataInstrument]:
    """Cherche l'instrument actif correspondant au symbol fourni.

    Match par `symbol` (DB) OU `provider_symbol`. Filtre par
    `is_active = "true"` (chaîne stockée).

    Note : la table ``market_data_instruments`` stocke pour les cryptos
    Binance le **provider symbol complet** (`BTCUSDT`) dans la colonne
    `symbol`, pas le short symbol (`BTC`). Pour qu'un appel
    ``execute(symbol="BTC")`` matche, on enrichit l'ensemble des
    candidates avec les quotes Binance courantes (USDT/USDC/BUSD).
    """
    candidates = {raw_symbol, short_symbol}
    if raw_symbol == short_symbol and raw_symbol:
        for quote in ("USDT", "USDC", "BUSD"):
            candidates.add(f"{raw_symbol}{quote}")
    candidates.discard("")
    if not candidates:
        return None
    return (
        db.query(MarketDataInstrument)
        .filter(
            or_(
                MarketDataInstrument.symbol.in_(candidates),
                MarketDataInstrument.provider_symbol.in_(candidates),
            ),
            MarketDataInstrument.is_active == "true",
        )
        .first()
    )


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["SPEC", "execute"]
