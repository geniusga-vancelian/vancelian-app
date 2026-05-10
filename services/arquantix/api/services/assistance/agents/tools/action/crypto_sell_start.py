"""Tool ``crypto_sell_start`` — CTA vendre via deep-link instrument (whitelist)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from database import MarketDataInstrument
from sqlalchemy import or_

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared.action_cta_catalog import build_action

from ._widget import append_action_widget

logger = logging.getLogger(__name__)

_ALLOWED_SYMBOLS: frozenset[str] = frozenset(
    {
        "BTC", "ETH", "USDT", "USDC", "SOL", "XRP",
        "ADA", "AVAX", "DOT", "DOGE", "TRX",
    }
)


def _normalize_short_symbol(raw: str) -> str:
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


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "crypto_sell_start",
        "description": (
            "Guide la vente d'un crypto : bouton sécurisé vers le flux "
            "sell natif (deep-link whitelisté **après** contrôle instrument)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "BTC, ETH, …"},
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "action",
}


def execute(
    ctx: ToolContext,
    *,
    symbol: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    raw = (symbol or "").strip().upper()
    short = _normalize_short_symbol(raw)
    if not short:
        return {"ok": False, "error": "missing_symbol"}

    if short not in _ALLOWED_SYMBOLS:
        return {
            "ok": False,
            "error": "unsupported_instrument",
            "supported_symbols": sorted(_ALLOWED_SYMBOLS),
        }

    inst = _resolve_instrument(ctx.db, raw, short)
    if inst is None:
        return {"ok": False, "error": "instrument_not_found", "symbol": short}

    cta = build_action(
        "sell_instrument",
        params={"instrument_id": str(inst.id)},
    )
    if not cta:
        return {"ok": False, "error": "cta_build_failed"}

    draft_id = append_action_widget(
        ctx,
        widget_kind="crypto_sell_cta",
        title=f"Vendre {short}",
        actions=[
            {"kind": cta["kind"], "label": cta["label"], "deep_link": cta["deep_link"]},
        ],
        disclaimer=(
            "Contrôle tes soldes dans l'application avant confirmation — "
            "les montants ne sont pas exécutés depuis le chat."
        ),
        action_type="crypto_sell_guide",
        payload={"symbol": short, "instrument_id": int(inst.id)},
    )
    if draft_id is None:
        return {
            "ok": False,
            "error": "client_required",
            "symbol": short,
        }

    logger.info(
        "crypto_sell_start conv=%s sym=%s draft=%s",
        ctx.conversation_id,
        short,
        draft_id,
    )
    return {
        "ok": True,
        "symbol": short,
        "instrument_id": int(inst.id),
        "action_draft_id": draft_id,
        "message": "Widget de vente affiché — ouverture flux natif après tap.",
    }
