"""
Repository for MarketDataLatestQuote (snapshot of latest price per instrument).
Caller is responsible for committing the session.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote


def get_latest_quotes_by_instrument_ids(
    session: Session,
    instrument_ids: List[int],
) -> List[MarketDataLatestQuote]:
    """
    Get latest quote rows for the given instrument IDs.

    Args:
        session: Database session (caller commits).
        instrument_ids: List of instrument IDs.

    Returns:
        List of MarketDataLatestQuote; may be shorter than instrument_ids if some have no quote.
    """
    if not instrument_ids:
        return []
    return (
        session.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.instrument_id.in_(instrument_ids))
        .all()
    )


def get_latest_quotes_by_symbols(
    session: Session,
    symbols: List[str],
) -> List[MarketDataLatestQuote]:
    """
    Get latest quote rows for the given instrument symbols (internal symbol, not provider_symbol).

    Args:
        session: Database session (caller commits).
        symbols: List of instrument symbols (e.g. ["BTC", "ETH"]).

    Returns:
        List of MarketDataLatestQuote; may be shorter than symbols if some have no quote.
    """
    if not symbols:
        return []
    return (
        session.query(MarketDataLatestQuote)
        .join(MarketDataInstrument, MarketDataLatestQuote.instrument_id == MarketDataInstrument.id)
        .filter(MarketDataInstrument.symbol.in_(symbols))
        .all()
    )


def get_latest_quotes_by_provider_symbols(
    session: Session,
    provider_symbols: List[str],
) -> List[MarketDataLatestQuote]:
    """
    Get latest quote rows for the given provider/market symbols (e.g. BTCUSDT).

    Args:
        session: Database session (caller commits).
        provider_symbols: List of provider symbols (e.g. ["BTCUSDT", "ETHUSDT"]).

    Returns:
        List of MarketDataLatestQuote; may be shorter than provider_symbols if some have no quote.
    """
    if not provider_symbols:
        return []
    return (
        session.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.provider_symbol.in_(provider_symbols))
        .all()
    )


def quotes_to_payload(
    quotes: List[MarketDataLatestQuote],
    eurusdt_rate: Optional[float] = None,
) -> List[dict]:
    """
    Convert a list of MarketDataLatestQuote to the API payload format (shared by REST and WebSocket).
    When eurusdt_rate is provided, includes a price_eur field for each quote.
    """
    out = []
    for q in quotes:
        symbol = q.provider_symbol or ""
        try:
            price = float(q.last_price)
        except (TypeError, ValueError):
            price = 0.0
        entry = {
            "instrument_id": q.instrument_id,
            "symbol": symbol,
            "price": price,
            "bid_price": float(q.bid_price) if q.bid_price is not None else None,
            "ask_price": float(q.ask_price) if q.ask_price is not None else None,
            "volume": float(q.volume) if q.volume is not None else None,
            "quote_time": q.quote_time.isoformat() if q.quote_time else None,
            "updated_at": q.updated_at.isoformat() if q.updated_at else None,
        }
        if eurusdt_rate and eurusdt_rate > 0:
            entry["price_eur"] = price / eurusdt_rate
        out.append(entry)
    return out


def upsert_latest_quote(
    session: Session,
    *,
    instrument_id: int,
    provider: str,
    provider_symbol: Optional[str],
    last_price: float,
    bid_price: Optional[float] = None,
    ask_price: Optional[float] = None,
    volume: Optional[float] = None,
    quote_time: Optional[object] = None,
) -> MarketDataLatestQuote:
    """
    Insert or update the latest quote for one instrument (one row per instrument).
    Caller must commit the session.

    Args:
        session: Database session (caller commits).
        instrument_id: Instrument ID.
        provider: Provider name (e.g. "binance").
        provider_symbol: Symbol as used by the provider (e.g. "BTCUSDT").
        last_price: Last traded price.
        bid_price: Best bid (optional).
        ask_price: Best ask (optional).
        volume: Volume (optional).
        quote_time: Timestamp of the quote from the provider (optional).

    Returns:
        The created or updated MarketDataLatestQuote instance.
    """
    row = (
        session.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.instrument_id == instrument_id)
        .first()
    )
    if row:
        row.provider = provider
        row.provider_symbol = provider_symbol
        row.last_price = last_price
        row.bid_price = bid_price
        row.ask_price = ask_price
        row.volume = volume
        row.quote_time = quote_time
        row.updated_at = datetime.now(timezone.utc)
        session.flush()
        session.refresh(row)
        return row
    row = MarketDataLatestQuote(
        instrument_id=instrument_id,
        provider=provider,
        provider_symbol=provider_symbol,
        last_price=last_price,
        bid_price=bid_price,
        ask_price=ask_price,
        volume=volume,
        quote_time=quote_time,
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return row
