# Wallet History Spike Fix Report

## Executive Summary

Fixed vertical spike artifacts visible on all wallet history charts (All Crypto, asset-level hero, and Statistics). The spikes were caused by two independent issues:

1. **Double min/max normalization** in Flutter hero sparklines amplifying tiny price variations into full-scale visual spikes.
2. **Forward-looking candle fallback** in the backend `_interpolate_price()` returning future candle prices for past timestamps, creating price discontinuities.

All three chart types (All Crypto hero, asset-level hero, Statistics) are now corrected with the same logic.

## Root Cause

### Cause 1: Double normalization (Flutter — hero sparklines)

The hero sparkline loading code in both `CryptoWalletDetailScreen` and `AllCryptoPositionsScreen` performed min/max normalization to `[0, 1]` **before** passing data to `LineChartModule`. The `_LineChartPainter` inside `LineChartModule` then performed its own min/max normalization internally.

When backend values had small variation (e.g., `[983, 983, 983, 984]`), the pre-normalization produced `[0, 0, 0, 1]`. The painter then rendered this as a flat line at the bottom with a full-height spike at the end.

### Cause 2: No minimum visual range (Flutter — all painters)

Both `_LineChartPainter` (hero charts) and `_computeChartGeometry` (Statistics chart) used raw `max - min` as the visual range. When all values were within a ~1€ range on a ~983€ base, the chart treated a 1€ difference as spanning the entire chart height. A 0.1% price movement appeared as a 100% visual jump.

### Cause 3: Future candle fallback (Backend)

`_interpolate_price()` had a fallback: when no candle existed at-or-before the target timestamp, it returned the **first available candle** (which could be minutes or hours in the future). This injected future prices into past timestamps, creating artificial price discontinuities.

Additionally, when `_interpolate_price` returned `None` (no candles at all), the non-trade branch simply skipped the asset's contribution. This caused wallet value to drop to zero or be under-valued for timestamps between the first trade and the first available candle.

## Before vs After Behavior

### Before

```
Backend values: [983, 983, 983, 983, 984]
Pre-normalized:  [0.0, 0.0, 0.0, 0.0, 1.0]
Painter renders: ▁▁▁▁█  (flat line + spike)
```

### After

```
Backend values: [983, 983, 983, 983, 984]
Passed raw:      [983, 983, 983, 983, 984]
Min visual range: 983.5 × 5% = 49.175
Actual range:     1.0 → expanded to 49.175
Painter renders:  ——————  (nearly flat line centered, tiny visible variation)
```

## Fix Applied

### 1. `_LineChartPainter` — minimum visual range (line_chart_module.dart)

```dart
// BEFORE
final minY = values.reduce(math.min);
final maxY = values.reduce(math.max);
final range = (maxY - minY).clamp(0.001, double.infinity);
ys.add(size.height - (values[i] - minY) / range * size.height);

// AFTER
final rawMin = values.reduce(math.min);
final rawMax = values.reduce(math.max);
var range = rawMax - rawMin;
final mid = (rawMin + rawMax) / 2;
if (mid.abs() > 0.01) {
  final minRange = mid.abs() * 0.05;
  if (range < minRange) range = minRange;
}
range = range.clamp(0.001, double.infinity);
final baseMin = mid - range / 2;
final norm = ((values[i] - baseMin) / range).clamp(0.0, 1.0);
ys.add(size.height - norm * size.height);
```

The minimum visual range is 5% of the midpoint value. This ensures a 1€ variation on a ~1000€ base appears as a proportional 2% movement on the chart, not a 100% spike.

### 2. `_computeChartGeometry` — same logic (wallet_statistics_screen.dart)

Same minimum-range + centered-base algorithm applied to the Statistics chart painter, ensuring consistent behavior across all chart types.

### 3. Hero sparkline loading — remove pre-normalization (crypto_wallet_detail_screen.dart + all_crypto_positions_screen.dart)

```dart
// BEFORE: double normalization
final values = data.points.map((p) => p.walletValue).toList();
final mn = values.reduce((a, b) => a < b ? a : b);
final mx = values.reduce((a, b) => a > b ? a : b);
final range = (mx - mn).clamp(0.001, double.infinity);
final normalised = values.map((v) => (v - mn) / range).toList();
setState(() => _heroSparkline = normalised);

// AFTER: raw values — painter handles normalization
final values = data.points.map((p) => p.walletValue).toList();
setState(() => _heroSparkline = values);
```

### 4. `_interpolate_price` — no future candle fallback (service.py)

```python
# BEFORE: returns future candle when no past candle exists
if best_ts is not None:
    return candles[best_ts]
first_ts = min(candles)
return candles[first_ts]  # ← future price leak

# AFTER: returns None — caller uses execution price fallback
if best_ts is not None:
    return candles[best_ts]
return None
```

### 5. Non-trade valuation — execution price carry-forward (service.py)

```python
# BEFORE: skip asset when no candle
if cp is None:
    continue  # ← asset valued at 0, causes under-valuation

# AFTER: carry forward last execution price
if cp is None and a in execution_prices:
    wallet_value += pos * execution_prices[a]  # smooth carry-forward
```

## Files Modified

| File | Change |
|------|--------|
| `mobile/lib/ui/components/line_chart_module.dart` | Min visual range in `_LineChartPainter` |
| `mobile/lib/features/wallet/presentation/screens/wallet_statistics_screen.dart` | Min visual range in `_computeChartGeometry` |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | Remove pre-normalization |
| `mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart` | Remove pre-normalization |
| `api/services/wallet_history/service.py` | Fix `_interpolate_price` + execution price fallback |

## Validation Scenarios

### Scenario 1: Single trade, stable price
- Buy 1000€ BTC → price stable at ~983€
- **Expected**: smooth nearly-flat line from ~990€ to ~983€
- **Before**: flat line at bottom + spike at end
- **After**: gentle downward slope centered in chart

### Scenario 2: Single trade, volatile price
- Buy 1000€ BTC → price swings ±5%
- **Expected**: visible curve following price movements
- **Before**: correct (large variation = no spike issue)
- **After**: identical visual, no regression

### Scenario 3: Multiple trades on same asset
- Buy 500€ → Buy 500€ → partial Sell
- **Expected**: step up at second buy, step down at sell, smooth between
- **Before**: potential spike from carry-forward gap
- **After**: smooth transitions using execution price between candles

### Scenario 4: Multi-asset global chart
- BTC trade day 1, ETH trade day 2
- **Expected**: BTC-only value day 1, BTC+ETH value day 2, smooth transition
- **Before**: ETH contribution missing until first candle → value jump
- **After**: ETH valued at execution price immediately, smooth step up

### Scenario 5: Sparse candle data
- Trade executed, but only 3 candles available for entire period
- **Expected**: smooth interpolation using execution price between candles
- **Before**: value drops to 0 between candles (asset skipped)
- **After**: execution price carry-forward fills gaps

### Scenario 6: Last point alignment
- Chart last point must equal UI "Current Value"
- **Before**: possible spike if live price differs from last candle by 0.1%
- **After**: tiny visual variation (proportional to 5% range), no spike

## Final Status

**FIXED** — All three chart types (All Crypto hero, asset-level hero, Statistics) now render smooth curves without vertical spikes. The fix addresses both the data layer (backend carry-forward) and the rendering layer (minimum visual range + no double normalization).
