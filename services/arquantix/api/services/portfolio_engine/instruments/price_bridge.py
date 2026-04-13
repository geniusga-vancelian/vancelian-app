"""
Read-only bridge: resolve the current market quote for a PE instrument
by looking up its market_data_instrument_id in the legacy market_data tables.

No data duplication.  No new table.  No valuation engine.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import MarketDataLatestQuote
from .models import Instrument
from ..assets.models import Asset


class InstrumentNotFoundError(Exception):
    def __init__(self, instrument_id: UUID):
        super().__init__(f"Instrument {instrument_id} not found")


class MarketDataLinkMissingError(Exception):
    """PE instrument exists but has no market_data_instrument_id in metadata."""

    def __init__(self, instrument_id: UUID):
        super().__init__(
            f"Instrument {instrument_id} has no market_data_instrument_id in metadata"
        )


class QuoteNotAvailableError(Exception):
    """No quote row exists in market_data_latest_quotes for this instrument."""

    def __init__(self, market_data_instrument_id: int):
        super().__init__(
            f"No quote available for market_data_instrument_id={market_data_instrument_id}"
        )


def get_instrument_price(db: Session, instrument_id: UUID) -> dict:
    """
    Resolve the current price for a PE instrument via the legacy
    market_data_latest_quotes table.

    Returns a plain dict ready for serialisation (not an ORM object).
    """
    instrument = (
        db.query(Instrument)
        .filter(Instrument.id == instrument_id)
        .first()
    )
    if instrument is None:
        raise InstrumentNotFoundError(instrument_id)

    metadata = instrument.metadata_ or {}
    md_id = metadata.get("market_data_instrument_id")
    if md_id is None:
        raise MarketDataLinkMissingError(instrument_id)

    md_id_int = int(md_id)

    quote: Optional[MarketDataLatestQuote] = (
        db.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.instrument_id == md_id_int)
        .first()
    )
    if quote is None:
        raise QuoteNotAvailableError(md_id_int)

    asset: Optional[Asset] = (
        db.query(Asset)
        .filter(Asset.id == instrument.asset_id)
        .first()
    )

    return {
        "instrument_id": str(instrument.id),
        "instrument_code": instrument.code,
        "asset_symbol": asset.symbol if asset else None,
        "market_data_instrument_id": md_id_int,
        "provider": quote.provider,
        "provider_symbol": quote.provider_symbol,
        "price": str(quote.last_price) if quote.last_price is not None else None,
        "bid_price": str(quote.bid_price) if quote.bid_price is not None else None,
        "ask_price": str(quote.ask_price) if quote.ask_price is not None else None,
        "volume_24h": str(quote.volume) if quote.volume is not None else None,
        "quote_time": quote.quote_time.isoformat() if quote.quote_time else None,
        "updated_at": quote.updated_at.isoformat() if quote.updated_at else None,
    }
