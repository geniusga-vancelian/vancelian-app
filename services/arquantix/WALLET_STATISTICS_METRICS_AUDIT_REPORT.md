# Wallet Statistics Metrics Audit Report

## Executive Summary

Three metric inconsistencies were identified and fixed:

| Metric | Bug | Severity | Fixed |
|--------|-----|----------|-------|
| Max Drawdown | Computed on ALL-TIME asset price history, not user's position | HIGH | YES |
| 30d Volatility | Included pre-position data when position < 30d old | MEDIUM | YES |
| Performance % chart | Could include pre-trade zero-value points as base | MEDIUM | YES |

Break-even Distance, Position Age, and P&L formulas were audited and found correct.

---

## Performance Chart Audit

### Before fix

```
series = wallet_history points (from GET /api/app/wallet/history)
base = _chartPoints.first.walletValue
performance_pct = (point.walletValue - base) / base × 100
```

**Problem:** The wallet history can include candle timestamps slightly before the first trade timestamp. At those timestamps, position = 0, so `wallet_value = 0`. When `base = 0`:
- `if (base > 0)` fails → falls back to absolute value mode (no crash, but wrong mode)
- If base is a tiny non-zero value → percentage explodes to thousands of %

### After fix

```dart
final firstNonZero = _chartPoints.indexWhere((p) => p.walletValue > 0);
final base = _chartPoints[firstNonZero].walletValue;
final relevant = _chartPoints.sublist(firstNonZero);
chartData = relevant.map((p) => (p.walletValue - base) / base * 100).toList();
```

Pre-trade zero-value points are excluded from both Performance % and absolute value modes. The base is always the first point with an actual position.

---

## Max Drawdown Audit

### Before fix

```python
def _compute_max_drawdown(db, instrument_id):
    rows = db.query(MarketDataBar1d.close)
        .filter(MarketDataBar1d.instrument_id == instrument_id)  # NO time filter
        .order_by(...)
```

**Formula:** Standard peak-to-trough: `dd = (close - peak) / peak`

**Problem:** Queried ALL daily candles for the instrument across the entire stored history. For BTC, this could include the 2021-2022 crash (~-50% or more). A user who bought BTC yesterday would see `-49.5%` max drawdown — completely unrelated to their position.

### After fix

```python
def _compute_max_drawdown(db, instrument_id, since=None):
    filters = [MarketDataBar1d.instrument_id == instrument_id]
    if since is not None:
        filters.append(MarketDataBar1d.open_time >= since)
    rows = db.query(MarketDataBar1d.close).filter(*filters)...
```

Called with `since=first_trade_at`. The drawdown now only reflects the asset's price movement since the user opened their position.

**Edge case:** If the position was opened today and there are < 2 daily candles since then, `max_drawdown = None` (correctly indicates insufficient data rather than showing misleading all-time data).

---

## Volatility Audit

### Before fix

```python
def _compute_volatility_30d(db, instrument_id):
    cutoff = now - timedelta(days=35)
    # No awareness of when position was opened
```

**Formula:** Annualised historical volatility from daily log-returns:
```
log_return_i = ln(close_i / close_{i-1})
daily_vol = stddev(log_returns)
annual_vol = daily_vol × √365
```

**Problem:** For a position opened 3 days ago, the volatility included 32 days of pre-position data. While this is a standard "asset volatility" metric, it could include anomalous periods before the user was exposed.

### After fix

```python
def _compute_volatility_30d(db, instrument_id, since=None):
    cutoff = now - timedelta(days=35)
    if since is not None and since > cutoff:
        cutoff = since
```

The 30d window is now bounded by `first_trade_at` when the position is less than 30 days old. This ensures the volatility reflects only the period during which the user held the asset.

**Note:** For a position < 3 days old, this correctly returns `None` (not enough data points for meaningful volatility).

---

## Root Cause

The original implementation treated volatility and drawdown as **asset-level market metrics** (similar to what you'd see on a Bloomberg terminal for the instrument). But on a **Wallet Statistics** page, these metrics should reflect the **user's position experience** — scoped to the period since they first traded.

This mismatch caused:
- A user who bought BTC yesterday seeing BTC's all-time -49.5% drawdown
- Volatility and drawdown coincidentally showing the same value (different calculations, same time window artifact)

---

## Fix Applied

### Backend (`api/services/wallet_statistics/service.py`)

1. `_compute_max_drawdown(db, instrument_id, since)` — added `since` parameter, filters candles to `open_time >= since`
2. `_compute_volatility_30d(db, instrument_id, since)` — added `since` parameter, bounds the 30d lookback window to no earlier than `since`
3. `build_wallet_statistics()` — passes `first_trade_at` to both functions

### Flutter (`wallet_statistics_screen.dart`)

4. Performance % chart — skips leading zero-value points, uses the first non-zero point as the normalisation base
5. Absolute value chart — also skips leading zeros for clean rendering

### Tests (`api/tests/test_wallet_statistics.py`)

6. `test_wallet_statistics_drawdown_scoped_to_position` — verifies that a -90% crash 200 days before the trade is excluded from the drawdown
7. `test_wallet_statistics_recent_trade_no_drawdown` — verifies that a very recent trade returns `None` drawdown when no daily candles exist since the trade

---

## Example After Fix

**Scenario:** Single BUY of 0.016 BTC at 62,119 €, position opened 2 hours ago.

| Metric | Before fix | After fix | Expected |
|--------|-----------|-----------|----------|
| Avg Entry (PRU) | 62,119 € | 62,119 € | Correct |
| Current Price | 62,010 € | 62,010 € | Correct |
| Break-even Distance | -0.2% | -0.2% | Correct |
| Unrealized P&L | -1.75 € | -1.75 € | Correct |
| Max Drawdown | -49.5% | None | Correct (no daily candles since trade) |
| 30d Volatility | 49.5% | None | Correct (< 3 daily data points) |
| Performance % chart | Spike from 0 → value | Clean curve from entry value | Correct |

**Scenario:** BUY of 0.01 BTC at 60,000 €, position opened 30 days ago, BTC went 60k→58k→63k.

| Metric | Before fix | After fix |
|--------|-----------|-----------|
| Max Drawdown | -49.5% (all-time BTC crash) | -3.3% (since position opened) |
| 30d Volatility | 49.5% (includes pre-position period) | ~25% (only since position) |

---

## Final Status

| Check | Status |
|-------|--------|
| Max Drawdown scoped to position | FIXED |
| 30d Volatility bounded by position start | FIXED |
| Performance % chart base value correct | FIXED |
| Pre-trade zero points excluded | FIXED |
| Break-even formula correct | VERIFIED |
| P&L formulas correct | VERIFIED |
| Position Age formula correct | VERIFIED |
| Tests passing (18/18) | YES |
| Regression on wallet history | NONE |

**All identified metric inconsistencies have been resolved.**
