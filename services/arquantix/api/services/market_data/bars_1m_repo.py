"""
Repository for MarketDataBar1m (1-minute OHLCV candles).
Caller is responsible for committing the session.
"""
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import MarketDataBar1m


def get_bars_1m(
    session: Session,
    instrument_id: int,
    start_time: Optional[object] = None,
    end_time: Optional[object] = None,
    limit: int = 500,
) -> List[MarketDataBar1m]:
    query = session.query(MarketDataBar1m).filter(
        MarketDataBar1m.instrument_id == instrument_id
    )
    if start_time is not None:
        query = query.filter(MarketDataBar1m.open_time >= start_time)
    if end_time is not None:
        query = query.filter(MarketDataBar1m.open_time <= end_time)
    return query.order_by(MarketDataBar1m.open_time).limit(limit).all()


def upsert_bar_1m(
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
) -> MarketDataBar1m:
    row = (
        session.query(MarketDataBar1m)
        .filter(
            and_(
                MarketDataBar1m.instrument_id == instrument_id,
                MarketDataBar1m.open_time == open_time,
            )
        )
        .first()
    )
    if row:
        return row
    row = MarketDataBar1m(
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
