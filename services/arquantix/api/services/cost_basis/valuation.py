"""Valorisation figée USD/EUR au moment de l'exécution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Optional

from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.exchange.assets import ASSET_PROVIDER_SYMBOL_MAP
from services.exchange.service import EUR_PEGGED_STABLECOINS, USD_PEGGED_STABLECOINS
from services.market_data.fx import EURUSDT_PROVIDER_SYMBOL, get_eurusdt_rate, usdt_to_eur

D18 = Decimal("0.00000001")
D10 = Decimal("0.01")

NativeQuoteKind = Literal["usdc", "eur", "crypto"]


@dataclass(frozen=True)
class FrozenExecutionValuation:
    native_quote_asset: str
    native_execution_price: Decimal
    native_notional: Decimal
    execution_price_usdc: Decimal
    execution_notional_usdc: Decimal
    execution_price_eur: Decimal
    execution_notional_eur: Decimal
    eurusd_rate_at_execution: Decimal
    fees_usdc: Decimal
    fees_eur: Decimal


def _dec(v: object) -> Decimal:
    return Decimal(str(v))


def _quantize18(v: Decimal) -> Decimal:
    return v.quantize(D18, rounding=ROUND_HALF_UP)


def _quantize10(v: Decimal) -> Decimal:
    return v.quantize(D10, rounding=ROUND_HALF_UP)


def classify_native_quote(asset: str) -> NativeQuoteKind:
    upper = asset.upper()
    if upper in EUR_PEGGED_STABLECOINS or upper == "EUR":
        return "eur"
    if upper in USD_PEGGED_STABLECOINS:
        return "usdc"
    return "crypto"


def _asset_usd_price(db: Session, asset: str) -> Decimal:
    """Prix unitaire USDC/USDT (≈ USD) depuis la quote marché."""
    upper = asset.upper()
    if upper in USD_PEGGED_STABLECOINS:
        return Decimal("1")
    if upper in EUR_PEGGED_STABLECOINS:
        rate = get_eurusdt_rate(db, strict=False)
        return _quantize18(rate)
    provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(upper, f"{upper}USDT")
    row = (
        db.query(MarketDataLatestQuote.last_price)
        .join(MarketDataInstrument, MarketDataLatestQuote.instrument_id == MarketDataInstrument.id)
        .filter(MarketDataInstrument.provider_symbol == provider_symbol)
        .first()
    )
    if row and row[0]:
        return _dec(row[0])
    raise ValueError(f"no_usd_price_for_{asset}")


def build_frozen_valuation(
    db: Session,
    *,
    position_asset: str,
    quantity: Decimal,
    quote_asset: str,
    quote_amount: Decimal,
    fee_quote_amount: Decimal = Decimal("0"),
    executed_at: Optional[datetime] = None,
) -> FrozenExecutionValuation:
    """Construit la triple valorisation (native, USD, EUR) pour une acquisition/disposal.

    *quote_amount* = montant total payé (acquisition) ou reçu (disposal) en *quote_asset*.
    *quantity* = quantité de *position_asset* échangée.
    """
    if quantity <= 0:
        raise ValueError("quantity_must_be_positive")
    if quote_amount <= 0:
        raise ValueError("quote_amount_must_be_positive")

    _ = executed_at or datetime.now(timezone.utc)
    eurusd = get_eurusdt_rate(db, strict=False)
    if eurusd <= 0:
        eurusd = Decimal("1.08")

    native_price = _quantize18(quote_amount / quantity)
    native_notional = _quantize18(quote_amount)
    fee_native = _quantize18(fee_quote_amount) if fee_quote_amount > 0 else Decimal("0")

    kind = classify_native_quote(quote_asset)

    if kind == "usdc":
        notional_usdc = native_notional + fee_native
        price_usdc = _quantize18(notional_usdc / quantity)
        notional_eur = _quantize18(usdt_to_eur(notional_usdc, eurusd))
        price_eur = _quantize18(notional_eur / quantity)
        fees_usdc = fee_native
        fees_eur = _quantize18(usdt_to_eur(fee_native, eurusd))
        native_quote = quote_asset.upper()

    elif kind == "eur":
        notional_eur = native_notional + fee_native
        price_eur = _quantize18(notional_eur / quantity)
        notional_usdc = _quantize18(notional_eur * eurusd)
        price_usdc = _quantize18(notional_usdc / quantity)
        fees_eur = fee_native
        fees_usdc = _quantize18(fee_native * eurusd)
        native_quote = "EUR"

    else:
        quote_usd = _asset_usd_price(db, quote_asset)
        notional_usdc = _quantize18(quote_amount * quote_usd) + _quantize18(fee_quote_amount * quote_usd)
        price_usdc = _quantize18(notional_usdc / quantity)
        notional_eur = _quantize18(usdt_to_eur(notional_usdc, eurusd))
        price_eur = _quantize18(notional_eur / quantity)
        fees_usdc = _quantize18(fee_quote_amount * quote_usd)
        fees_eur = _quantize18(usdt_to_eur(fees_usdc, eurusd))
        native_quote = quote_asset.upper()

    return FrozenExecutionValuation(
        native_quote_asset=native_quote,
        native_execution_price=native_price,
        native_notional=native_notional,
        execution_price_usdc=price_usdc,
        execution_notional_usdc=notional_usdc,
        execution_price_eur=price_eur,
        execution_notional_eur=notional_eur,
        eurusd_rate_at_execution=_quantize10(eurusd),
        fees_usdc=fees_usdc,
        fees_eur=fees_eur,
    )


def build_crypto_cross_valuation(
    db: Session,
    *,
    position_asset: str,
    quantity: Decimal,
    from_asset: str,
    from_amount: Decimal,
    fee_from_amount: Decimal = Decimal("0"),
    executed_at: Optional[datetime] = None,
) -> FrozenExecutionValuation:
    """Cas 3 : crypto ↔ crypto — notionnel USD/EUR figé via prix marché des deux jambes."""
    return build_frozen_valuation(
        db,
        position_asset=position_asset,
        quantity=quantity,
        quote_asset=from_asset,
        quote_amount=from_amount,
        fee_quote_amount=fee_from_amount,
        executed_at=executed_at,
    )
