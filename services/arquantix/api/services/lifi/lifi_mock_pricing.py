"""Estimation mock LI.FI — réutilise les quotes Binance (ExchangeService.preview_swap)."""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_DOWN

from database import SessionLocal
from services.exchange.assets import ASSET_PRECISION
from services.exchange.schemas import SwapPreviewRequest
from services.exchange.service import ExchangeError, ExchangeService

logger = logging.getLogger(__name__)


def estimate_mock_swap_output(
    *,
    from_asset: str,
    to_asset: str,
    amount_in: Decimal,
) -> Decimal:
    """Montant cible estimé via la même logique que le preview Exchange (Binance → EUR)."""
    from_sym = (from_asset or "").strip().upper()
    to_sym = (to_asset or "").strip().upper()
    if amount_in <= 0:
        return Decimal("0")

    db = SessionLocal()
    try:
        preview = ExchangeService().preview_swap(
            db,
            SwapPreviewRequest(
                from_asset=from_sym,
                to_asset=to_sym,
                amount_from=amount_in,
            ),
            currency="EUR",
        )
        out = Decimal(str(preview.get("estimated_to_amount", 0)))
        if out > 0:
            return out
    except ExchangeError as exc:
        logger.warning(
            "lifi.mock_pricing.exchange_failed from=%s to=%s amount=%s err=%s",
            from_sym,
            to_sym,
            amount_in,
            exc,
        )
    except Exception as exc:
        logger.warning(
            "lifi.mock_pricing.unexpected from=%s to=%s amount=%s err=%s",
            from_sym,
            to_sym,
            amount_in,
            exc,
        )
    finally:
        db.close()

    return _fallback_output(from_sym, to_sym, amount_in)


def _fallback_output(from_sym: str, to_sym: str, amount_in: Decimal) -> Decimal:
    """Dernier recours si quotes Binance indisponibles (dev uniquement)."""
    decimals = ASSET_PRECISION.get(to_sym, 8)
    quant = Decimal(10) ** -decimals
    if from_sym in {"USDC", "USDT", "EURC"} and to_sym not in {"USDC", "USDT", "EURC"}:
        return (amount_in * Decimal("0.00001")).quantize(quant, rounding=ROUND_DOWN)
    return amount_in.quantize(quant, rounding=ROUND_DOWN)
