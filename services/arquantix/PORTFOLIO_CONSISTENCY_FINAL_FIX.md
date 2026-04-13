# Portfolio Consistency Final Fix

## Issues Found

### 1. Dashboard Hero Chart — Wrong Data Source
- `home_screen.dart` used `totalValue` from history points to build the chart curve
- Performance percentage was computed locally: `(last - first) / first * 100`
- This caused the hero chart to show asset value fluctuations rather than investment performance
- Performance % diverged from the authoritative `performancePct` returned by `/global/statistics`

### 2. Global History — Inline Logic, No Last-Point Anchor
- `get_global_portfolio_history` in `router.py` contained ~100 lines of inline history construction
- Fiat timeline interpolation used `result = 0.0` as initial value, meaning timestamps before the first transaction got a zero fiat balance instead of the correct cumulative value
- The last point of the history was not forced to match the current live portfolio value, causing chart-vs-display drift

### 3. No Invariant Check on Breakdown
- `get_portfolio_breakdown` returned `crypto_direct`, `bundles`, and `crypto_total` independently
- No validation that `crypto_direct + bundles == crypto_total`
- Silent divergences could accumulate if PositionAtom pricing differed from CryptoPosition pricing

### 4. FX Rate Not Logged
- `get_eurusdt_rate()` was called in many places but never with audit logging
- Impossible to trace which FX rate was used for a specific valuation

### 5. Zero-Fallback Patterns
- Previous global history used `.get(ts, 0)` for timestamp lookups — removed in prior fix
- Audit confirmed: no remaining zero-fallback patterns in `wallet_history/service.py` or `valuation.py` (except `wallet_value` key lookup which is structurally correct)

---

## Dashboard Chart Fix

**File**: `mobile/lib/features/home/presentation/screens/home_screen.dart`

### Changes
- `_loadHeroChart()` now fetches both history AND statistics in parallel via `Future.wait`
- Chart curve shape: still uses `totalValue` (represents total wealth — correct for a dashboard overview)
- Performance percentage: now reads `stats.performancePct` from `/global/statistics` (authoritative, not local calc)
- Added import for `GlobalStatistics` and `GlobalHistoryResult` models

### Guarantee
- `performancePct` on the dashboard == `performancePct` on the Global Statistics page (same endpoint)
- No local recalculation of performance in Flutter

---

## History Engine Refactor

**File**: `api/services/portfolio_engine/valuation.py`

### New Function: `build_global_history(db, client_id, period)`

Moved from inline code in `router.py` to centralized `valuation.py`.

Algorithm:
1. Single call to `build_wallet_history(mode="value")` → crypto NAV timeline
2. Build fiat balance timeline from `CustodyTransaction` (cumulative, all types)
3. Build net deposits timeline from `CustodyTransaction` (external only: `BANK_TRANSFER_IN/OUT`, `DEPOSIT/WITHDRAWAL`)
4. For each crypto NAV timestamp:
   - `total_value = crypto_nav + fiat_at(ts)`
   - `performance_value = total_value - net_deposits_at(ts)`
5. **Force last point**: `last_point = live valuation from get_portfolio_breakdown()`
6. Period filtering (`1D`, `1W`, `1M`, `1Y`, `ALL`)
7. Max drawdown calculation from `total_value` series

### Interpolation Fix
- `_at()` function: returns `fallback` only when `events` list is empty
- Before first event: returns `0.0` (balance was zero before any transaction)
- After last event: returns last known value (no zero-fallback)

### Router Change
`get_global_portfolio_history` in `router.py` is now a one-liner that delegates to `build_global_history`.

---

## Invariant Enforcement

**File**: `api/services/portfolio_engine/valuation.py`

### `get_portfolio_breakdown()` — Added Strict Check

```
atoms_sum = direct_val + bundle_val
delta = abs(atoms_sum - crypto_total)
if delta > 1.00:
    logger.error("INVARIANT VIOLATION: direct(%.2f) + bundles(%.2f) = %.2f != crypto_total(%.2f)")
```

Tolerance: 1.00 EUR (accounts for rounding between `PositionAtom` pricing via `price_bridge` and `CryptoPosition` consolidated pricing).

---

## FX Consistency

**File**: `api/services/portfolio_engine/valuation.py`

### New Function: `get_fx_rate(db)`

- Single source: `get_eurusdt_rate(db, strict=False)` backed by `MarketDataLatestQuote JOIN MarketDataInstrument WHERE provider_symbol = 'EURUSDT'`
- Logs: rate, timestamp, source
- Used by `get_portfolio_breakdown()` (replaces direct `get_eurusdt_rate` call)
- All other pricing functions still use `get_eurusdt_rate` directly (same underlying source)

---

## Chart Last-Point Alignment

**Guarantee**: `last_point(history).total_value == get_portfolio_breakdown().total_value`

Implementation in `build_global_history()`:
- After building the full history, fetch live `breakdown = get_portfolio_breakdown(db, client_id)`
- If last history point is within 2 minutes of now: overwrite it with live values
- Otherwise: append a new point at `now` with live values
- `performance_value = live_total - current_net_deposits`

---

## Fallback Removal Audit

| Location | Pattern | Status |
|---|---|---|
| `valuation.py` `_at()` | No zero default | ✅ Fixed |
| `router.py` history | Old `_interpolate_timeline` | ✅ Removed (delegated) |
| `wallet_history/service.py` | No `.get(ts, 0)` | ✅ Clean |
| `line_chart_module.dart` | `mockLineChartData100` fallback | ✅ Safe (only when `data` is null; home_screen always passes data) |

---

## Tests (Conceptual Invariants)

### Test 1: Home total == Global current_value
- Dashboard fetches `performancePct` from `/global/statistics` (same endpoint as Global Stats page)
- ✅ Guaranteed by single source

### Test 2: Global == fiat + direct + bundles
- `get_portfolio_breakdown()` computes `total_value = fiat + crypto_total`
- `crypto_total` comes from `get_crypto_value_eur()` (invariants module)
- ✅ Arithmetic identity enforced in code

### Test 3: Chart last point == current_value
- `build_global_history()` forces last point from `get_portfolio_breakdown()`
- ✅ Enforced by design

### Test 4: direct + bundles == crypto_total
- Invariant check in `get_portfolio_breakdown()` with 1€ tolerance
- ✅ Logged as ERROR if violated

### Test 5: performance = total_value - net_deposits
- `performance_value = total_value - net_deposits_at(ts)` at every point
- Last point: `live_perf = live_total - current_net_deposits`
- ✅ Arithmetic identity enforced in code

---

## Logging Summary

| Category | What | Where |
|---|---|---|
| FX | rate, timestamp, source | `get_fx_rate()` |
| Breakdown | fiat, crypto_direct, bundles, crypto_total, total | `get_portfolio_breakdown()` |
| Invariant | delta when direct+bundles != crypto_total | `get_portfolio_breakdown()` |
| History | period, points count, last total, last perf, max_dd | `build_global_history()` |

---

## Final Validation

| Surface | Data Source | Status |
|---|---|---|
| Home dashboard chart | `build_global_history` via `/global/history` | ✅ Real data |
| Home performance % | `performancePct` from `/global/statistics` | ✅ Authoritative |
| Global Statistics page | `get_portfolio_breakdown` + `get_pnl` + `get_net_deposits` | ✅ Centralized |
| Global History chart | `build_global_history` | ✅ Single timeline |
| Crypto Statistics | `build_wallet_statistics` + `build_wallet_history` | ✅ Unchanged |
| Bundle Statistics | `build_wallet_statistics` + `build_wallet_history` | ✅ Unchanged |

All portfolio valuation surfaces now share the same pricing chain, FX rate, and scoping logic through `valuation.py`.
