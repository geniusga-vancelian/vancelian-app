"""Valorisation positions bundle — stablecoins 1:1, actifs volatils via market data."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
from services.portfolio_engine.instruments.price_bridge import get_instrument_price

_QUANT = Decimal("0.01")
_RHU = ROUND_HALF_UP
_STABLE_USD = frozenset({"USDC", "USDT"})
_STABLE_EUR = frozenset({"EUR", "EURC"})


def _q(value: Decimal) -> Decimal:
    return value.quantize(_QUANT, rounding=_RHU)


def resolve_bundle_position_market_values(
    db: Session,
    *,
    symbol: str,
    quantity: Decimal,
    instrument_id: UUID,
    eurusdt_rate: Decimal | None = None,
) -> dict[str, Decimal | None]:
    """Prix et valorisation EUR/USD d'une position bundle (atom ou cible 0 qty)."""
    sym = (symbol or "").strip().upper()
    qty = Decimal(str(quantity or 0))
    rate = eurusdt_rate if eurusdt_rate is not None else get_eurusdt_rate(db, strict=False)

    if sym in _STABLE_USD:
        price_usd = Decimal("1")
        price_eur = usdt_to_eur(Decimal("1"), rate)
        market_value_usd = _q(qty) if qty > 0 else None
        market_value = _q(qty * price_eur) if qty > 0 else None
        return {
            "price_usd": price_usd,
            "price_eur": price_eur,
            "market_value_usd": market_value_usd,
            "market_value": market_value,
        }

    if sym in _STABLE_EUR:
        price_eur = Decimal("1")
        price_usd = _q(rate)
        market_value = _q(qty) if qty > 0 else None
        market_value_usd = _q(qty * rate) if qty > 0 else None
        return {
            "price_usd": price_usd,
            "price_eur": price_eur,
            "market_value_usd": market_value_usd,
            "market_value": market_value,
        }

    price_usdt = None
    price_eur = None
    price_usd = None
    market_value = None
    market_value_usd = None
    try:
        price_info = get_instrument_price(db, instrument_id)
        price_usdt = Decimal(str(price_info["price"])) if price_info.get("price") else None
        if price_usdt is not None:
            price_usd = price_usdt
            price_eur = usdt_to_eur(price_usdt, rate)
            if qty > 0:
                market_value_usd = _q(qty * price_usdt)
                market_value = _q(qty * price_eur)
    except Exception:
        pass

    return {
        "price_usd": price_usd,
        "price_eur": price_eur,
        "market_value_usd": market_value_usd,
        "market_value": market_value,
    }


def eur_cost_basis_to_usd(cost_eur: Decimal, eurusdt_rate: Decimal) -> Decimal:
    """Convertit un cost basis PE (EUR) en équivalent USD affichage."""
    return _q(Decimal(str(cost_eur or 0)) * eurusdt_rate)
