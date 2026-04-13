"""EUR/USDT FX conversion utilities.

Single source of truth for converting USDT prices to EUR.
Uses the EURUSDT quote from market_data_latest_quotes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote

logger = logging.getLogger(__name__)

EURUSDT_PROVIDER_SYMBOL = "EURUSDT"
DEFAULT_EURUSDT_RATE = Decimal("1.08")
MAX_FX_QUOTE_AGE_SECONDS = 300


def get_eurusdt_rate(db: Session, *, strict: bool = False) -> Decimal:
    """Return the current EUR/USDT exchange rate.

    When strict=True (e.g. for exchange trades), raises if the quote is
    missing or stale (> MAX_FX_QUOTE_AGE_SECONDS).

    When strict=False (e.g. for display/valuation), falls back to
    DEFAULT_EURUSDT_RATE if unavailable.
    """
    quote = (
        db.query(MarketDataLatestQuote)
        .join(MarketDataInstrument, MarketDataLatestQuote.instrument_id == MarketDataInstrument.id)
        .filter(MarketDataInstrument.provider_symbol == EURUSDT_PROVIDER_SYMBOL)
        .first()
    )

    if quote is None or quote.last_price is None:
        if strict:
            raise FxQuoteUnavailableError("eurusdt_quote_not_found")
        logger.warning("EURUSDT quote not found, using default rate %s", DEFAULT_EURUSDT_RATE)
        return DEFAULT_EURUSDT_RATE

    rate = Decimal(str(quote.last_price))
    if rate <= 0:
        if strict:
            raise FxQuoteUnavailableError("eurusdt_rate_is_zero")
        return DEFAULT_EURUSDT_RATE

    if strict and quote.updated_at:
        updated = quote.updated_at if quote.updated_at.tzinfo else quote.updated_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        if age > MAX_FX_QUOTE_AGE_SECONDS:
            raise FxQuoteStaleError(
                f"eurusdt_quote_stale: age={int(age)}s, max={MAX_FX_QUOTE_AGE_SECONDS}s"
            )

    return rate


def usdt_to_eur(usdt_price: Decimal, eurusdt_rate: Decimal) -> Decimal:
    """Convert a USDT price to EUR: price_eur = price_usdt / eurusdt_rate."""
    if eurusdt_rate <= 0:
        return usdt_price
    return usdt_price / eurusdt_rate


class FxQuoteUnavailableError(Exception):
    pass


class FxQuoteStaleError(Exception):
    pass
