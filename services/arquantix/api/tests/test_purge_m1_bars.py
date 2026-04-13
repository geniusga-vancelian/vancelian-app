"""Tests for M1 bars purge service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from database import MarketDataBar1m, MarketDataInstrument
from services.market_data.purge_m1_bars import run_purge_m1_bars


def _ensure_instrument(db: Session, symbol: str = "BTCUSDT") -> int:
    existing = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.symbol == symbol,
    ).first()
    if existing:
        return existing.id
    inst = MarketDataInstrument(
        symbol=symbol,
        name=symbol,
        asset_class="crypto",
        provider="binance",
        provider_symbol=symbol,
        is_active="true",
    )
    db.add(inst)
    db.flush()
    return inst.id


def _insert_bar_1m(db: Session, instrument_id: int, open_time: datetime) -> None:
    bar = MarketDataBar1m(
        instrument_id=instrument_id,
        open_time=open_time,
        open=Decimal("90000"),
        high=Decimal("90000"),
        low=Decimal("90000"),
        close=Decimal("90000"),
        volume=Decimal("100"),
        source="binance",
    )
    db.add(bar)
    db.flush()


def test_purge_deletes_old_keeps_recent(db: Session):
    """Old bars (>24h) are deleted, recent bars (<24h) are kept."""
    iid = _ensure_instrument(db)
    now = datetime.now(timezone.utc)

    old_time = now - timedelta(hours=48)
    recent_time = now - timedelta(hours=1)

    _insert_bar_1m(db, iid, old_time)
    _insert_bar_1m(db, iid, recent_time)

    count_before = db.query(MarketDataBar1m).filter(
        MarketDataBar1m.instrument_id == iid,
    ).count()
    assert count_before == 2

    deleted = run_purge_m1_bars(db)

    assert deleted >= 1

    remaining = db.query(MarketDataBar1m).filter(
        MarketDataBar1m.instrument_id == iid,
    ).all()
    assert len(remaining) == 1
    assert remaining[0].open_time == recent_time


def test_purge_empty_table(db: Session):
    """Purge on empty table returns 0 without error."""
    deleted = run_purge_m1_bars(db)
    assert deleted == 0


def test_purge_does_not_touch_recent(db: Session):
    """All recent bars survive the purge."""
    iid = _ensure_instrument(db)
    now = datetime.now(timezone.utc)

    times = [now - timedelta(minutes=m) for m in range(5)]
    for t in times:
        _insert_bar_1m(db, iid, t)

    deleted = run_purge_m1_bars(db)
    assert deleted == 0

    count = db.query(MarketDataBar1m).filter(
        MarketDataBar1m.instrument_id == iid,
    ).count()
    assert count == 5
