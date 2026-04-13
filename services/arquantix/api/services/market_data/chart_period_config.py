"""
Backend configuration for UI chart periods.
Maps app period keys (1j, 1s, 1m, 1a, 5a) to candle timeframe and lookback.
All logic lives here; frontend only sends period + symbol/instrument_id.
"""
from datetime import timedelta
from typing import NamedTuple, Optional

# Allowed UI period keys
CHART_PERIODS = ("1j", "1s", "1m", "1a", "5a")


class ChartPeriodRule(NamedTuple):
    """One rule: timeframe (candle table), lookback duration, max bars to return."""

    timeframe: str  # "5m", "1h", "4h", "1d", "1w"
    lookback: timedelta
    limit: int


# Explicit mapping: UI period -> (timeframe, lookback, max points = théorique dans la plage)
# Pas de plafond arbitraire : on retourne tous les points dans [start_time, end_time].
# 1j => last 24 hours using 5m candles -> 24*12 = 288
# 1s => last 7 days using 1h candles -> 7*24 = 168
# 1m => last 30 days using 4h candles -> 30*6 = 180
# 1a => last 365 days using 1d candles -> 365
# 5a => last 5 years using 1w candles -> ~260
CHART_PERIOD_RULES: dict[str, ChartPeriodRule] = {
    "1j": ChartPeriodRule(timeframe="5m", lookback=timedelta(hours=24), limit=288),
    "1s": ChartPeriodRule(timeframe="1h", lookback=timedelta(days=7), limit=168),
    "1m": ChartPeriodRule(timeframe="4h", lookback=timedelta(days=30), limit=180),
    "1a": ChartPeriodRule(timeframe="1d", lookback=timedelta(days=365), limit=365),
    "5a": ChartPeriodRule(timeframe="1w", lookback=timedelta(days=5 * 365), limit=260),
}


def get_chart_period_rule(period: str) -> Optional[ChartPeriodRule]:
    """Return the rule for a given UI period, or None if invalid."""
    return CHART_PERIOD_RULES.get(period)
