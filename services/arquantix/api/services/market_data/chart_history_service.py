"""
Chart history service: backend-driven chart range for UI period selectors.
Resolves symbol/instrument_id, applies period -> timeframe + lookback rules,
queries the correct candle table and returns a normalized payload.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database import MarketDataInstrument
from services.market_data.chart_period_config import get_chart_period_rule
from services.market_data.bars_5m_repo import get_bars_5m
from services.market_data.bars_1h_repo import get_bars_1h
from services.market_data.bars_4h_repo import get_bars_4h
from services.market_data.bars_1d_repo import get_bars_1d
from services.market_data.bars_1w_repo import get_bars_1w


def _normalize_bar(b: Any, provider_symbol: str) -> Dict[str, Any]:
    """Build one candle dict for the unified response."""
    return {
        "instrument_id": b.instrument_id,
        "symbol": provider_symbol,
        "open_time": b.open_time.isoformat() if b.open_time else None,
        "open": float(b.open),
        "high": float(b.high),
        "low": float(b.low),
        "close": float(b.close),
        "volume": float(b.volume),
    }


def get_chart_history(
    session: Session,
    *,
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    period: str,
) -> Optional[Dict[str, Any]]:
    """
    Return chart-ready candle array for the given asset and UI period.
    Backend applies timeframe and date range; frontend only sends symbol/instrument_id + period.

    Args:
        session: DB session.
        symbol: Provider symbol (e.g. BTCUSDT). Exactly one of symbol or instrument_id.
        instrument_id: Instrument ID. Exactly one of symbol or instrument_id.
        period: UI period: 1j, 1s, 1m, 1a, 5a.

    Returns:
        Dict with symbol, period, timeframe, start_time, end_time, candles; or None if
        instrument not found or period invalid (caller should validate period before calling).
    """
    rule = get_chart_period_rule(period)
    if not rule:
        return None

    # Resolve instrument
    if symbol:
        symbol = symbol.strip().upper()
        inst = (
            session.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == symbol)
            .first()
        )
    else:
        inst = (
            session.query(MarketDataInstrument)
            .filter(MarketDataInstrument.id == instrument_id)
            .first()
        )
    if not inst:
        return None

    resolved_id = inst.id
    provider_symbol = inst.provider_symbol or (symbol if symbol else "")

    # Backend-driven range in UTC
    end_time = datetime.now(timezone.utc)
    start_time = end_time - rule.lookback

    # Query the correct repo
    if rule.timeframe == "5m":
        bars = get_bars_5m(
            session,
            resolved_id,
            start_time=start_time,
            end_time=end_time,
            limit=rule.limit,
        )
    elif rule.timeframe == "1h":
        bars = get_bars_1h(
            session,
            resolved_id,
            start_time=start_time,
            end_time=end_time,
            limit=rule.limit,
        )
    elif rule.timeframe == "4h":
        bars = get_bars_4h(
            session,
            resolved_id,
            start_time=start_time,
            end_time=end_time,
            limit=rule.limit,
        )
    elif rule.timeframe == "1d":
        bars = get_bars_1d(
            session,
            resolved_id,
            start_time=start_time,
            end_time=end_time,
            limit=rule.limit,
        )
    elif rule.timeframe == "1w":
        bars = get_bars_1w(
            session,
            resolved_id,
            start_time=start_time,
            end_time=end_time,
            limit=rule.limit,
        )
    else:
        return None

    candles: List[Dict[str, Any]] = [_normalize_bar(b, provider_symbol) for b in bars]

    return {
        "symbol": provider_symbol,
        "period": period,
        "timeframe": rule.timeframe,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "candles": candles,
    }
