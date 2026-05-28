"""Cost basis bundle — toujours exprimé en EUR de référence (évite confusion USDC/EUR)."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from sqlalchemy.orm import Session

from services.exchange.schemas import SwapPreviewRequest
from services.exchange.service import ExchangeError, ExchangeService
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur

_EUR_QUANT = Decimal("0.01")
_STABLE_USD = frozenset({"USDC", "USDT"})
_STABLE_EUR = frozenset({"EUR", "EURC"})


def reference_cost_basis_eur(
    db: Session,
    asset: str,
    amount: Decimal,
    *,
    currency: str = "EUR",
) -> Decimal:
    """Convertit un montant funding/swap source en cost basis EUR (WAC / P&L bundle)."""
    sym = (asset or "").strip().upper()
    amt = Decimal(str(amount or 0))
    if amt <= 0:
        return Decimal("0")
    if sym in _STABLE_EUR:
        return amt.quantize(_EUR_QUANT, rounding=ROUND_DOWN)
    if sym in _STABLE_USD:
        return usdt_to_eur(amt, get_eurusdt_rate(db, strict=False)).quantize(
            _EUR_QUANT, rounding=ROUND_DOWN,
        )
    try:
        preview = ExchangeService().preview_swap(
            db,
            SwapPreviewRequest(
                from_asset=sym,
                to_asset=_quote_counter_asset(sym),
                amount_from=amt,
            ),
            currency=currency,
        )
        net = Decimal(str(preview.get("estimated_reference_value_net", 0)))
        if net > 0:
            return net.quantize(_EUR_QUANT, rounding=ROUND_DOWN)
    except ExchangeError:
        pass
    return amt.quantize(_EUR_QUANT, rounding=ROUND_DOWN)


def _quote_counter_asset(from_asset: str) -> str:
    if from_asset == "ETH":
        return "USDC"
    return "ETH"
