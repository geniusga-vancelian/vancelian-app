"""
Repository for MarketDataBar1h (1-hour OHLCV candles).
Caller is responsible for committing the session.
"""
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import MarketDataBar1h


def get_bars_1h(
    session: Session,
    instrument_id: int,
    start_time: Optional[object] = None,
    end_time: Optional[object] = None,
    limit: int = 300,
) -> List[MarketDataBar1h]:
    """
    Get 1h bars for one instrument, optionally filtered by time range.
    Results ordered by open_time ascending. Caller does not commit.

    Args:
        session: Database session.
        instrument_id: Instrument ID.
        start_time: Optional start (inclusive), timezone-aware datetime.
        end_time: Optional end (inclusive), timezone-aware datetime.
        limit: Max number of bars to return (default 300).

    Returns:
        List of MarketDataBar1h.
    """
    query = session.query(MarketDataBar1h).filter(
        MarketDataBar1h.instrument_id == instrument_id
    )
    if start_time is not None:
        query = query.filter(MarketDataBar1h.open_time >= start_time)
    if end_time is not None:
        query = query.filter(MarketDataBar1h.open_time <= end_time)
    return query.order_by(MarketDataBar1h.open_time).limit(limit).all()


def upsert_bar_1h(
    session: Session,
    *,
    instrument_id: int,
    open_time: object,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    source: str = "binance",
) -> MarketDataBar1h:
    """
    Insert one 1h bar if it does not exist. If a bar already exists for this instrument_id and
    open_time, it is left unchanged (no overwrite). Caller must commit.

    Args:
        session: Database session.
        instrument_id: Instrument ID.
        open_time: Bar open time (timezone-aware datetime).
        open, high, low, close, volume: OHLCV.
        source: Source identifier (default "binance").

    Returns:
        The existing or newly created MarketDataBar1h instance.
    """
    row = (
        session.query(MarketDataBar1h)
        .filter(
            and_(
                MarketDataBar1h.instrument_id == instrument_id,
                MarketDataBar1h.open_time == open_time,
            )
        )
        .first()
    )
    if row:
        return row  # ne pas écraser : conserver la barre existante
    row = MarketDataBar1h(
        instrument_id=instrument_id,
        open_time=open_time,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        source=source,
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return row
