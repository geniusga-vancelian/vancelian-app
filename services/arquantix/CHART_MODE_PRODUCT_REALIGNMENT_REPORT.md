# CHART_MODE_PRODUCT_REALIGNMENT_REPORT

## Executive Summary

A recent fix introduced a product regression: hero charts were switched to `mode: 'value'` (NAV) and statistics screens offered a "Performance %" toggle. This contradicted the intended product rule where all performance charts must display **monetary performance** (realized + unrealized P&L cumulated over time), not raw NAV or percentage.

This patch realigns all 4 affected Flutter screens with the correct product intent. No backend changes were required — the backend `performance_value` mode already produces the correct monetary series.

## Product Rule Restored

| Element | Rule |
|---|---|
| Headline amount (big number) | Current value (NAV) |
| Hero chart (sparkline) | `mode: 'performance_value'` — monetary P&L over time |
| Statistics chart | `mode: 'performance_value'` — monetary P&L, no toggle |
| No percentage mode | Removed from all screens |

The `performance_value` series represents `realized_pnl_cumulated(t) + unrealized_pnl(t)` — the true monetary performance starting from 0 at first trade.

## Wallet Detail Fix

**File**: `crypto_wallet_detail_screen.dart`

- **Before**: `_loadHeroSparkline()` used `mode: 'value'` (NAV)
- **After**: Changed to `mode: 'performance_value'`
- Headline amount unchanged — still shows current wallet value (NAV)
- Hero sparkline now shows monetary P&L history

## All Crypto Fix

**File**: `all_crypto_positions_screen.dart`

- **Before**: `_loadHeroSparkline()` used `mode: 'value'` (NAV) with `scope: 'crypto'`
- **After**: Changed to `mode: 'performance_value'` with `scope: 'crypto'`
- Headline amount unchanged — still shows total crypto portfolio value
- Hero sparkline now shows aggregated monetary P&L history

## Wallet Statistics Fix

**File**: `wallet_statistics_screen.dart`

- **Before**: Fetched both `value` and `performance_value` series; offered toggle "Value / Performance %"
- **After**:
  - Removed `_chartPointsValue` and `_chartPointsPerf` → single `_chartPoints`
  - Removed `_showPercent` state variable
  - Only fetches `mode: 'performance_value'` (1 API call instead of 2)
  - Removed `_ChartToggle` widget and toggle Row
  - Chart header now shows signed monetary amount colored green/red
  - `_computeChartGeometry` simplified (no % label logic)

## Portfolio Statistics Fix

**File**: `portfolio_statistics_screen.dart`

- **Before**: Same dual-mode fetch and "Value / Performance %" toggle as wallet statistics
- **After**:
  - Removed `_chartPointsValue` and `_chartPointsPerf` → single `_chartPoints`
  - Removed `_showPercent` state variable
  - Only fetches `mode: 'performance_value'` with `scope: 'crypto'` (1 API call instead of 2)
  - Removed `_ChartToggle` widget and toggle Row
  - Chart header shows signed monetary amount colored green/red
  - Overview section unchanged — still shows total portfolio value as headline

## API Mode Alignment

| Screen | API call | Mode |
|---|---|---|
| CryptoWalletDetailScreen hero | `/wallet/history?asset=X&period=ALL` | `performance_value` |
| AllCryptoPositionsScreen hero | `/wallet/history?scope=crypto&period=ALL` | `performance_value` |
| WalletStatisticsScreen chart | `/wallet/history?asset=X&period=P` | `performance_value` |
| PortfolioStatisticsScreen chart | `/wallet/history?scope=crypto&period=P` | `performance_value` |

All screens now use a single mode. No `value` mode is used for charts. The backend `build_wallet_history` service with `mode=performance_value` is the sole data source for all chart series.

## Final Status

- **Hero charts**: Restored to `performance_value` — monetary P&L ✅
- **Statistics charts**: Simplified to single `performance_value` mode ✅
- **"Performance %" toggle**: Removed from both statistics screens ✅
- **Backend unchanged**: No modifications to accounting or API layer ✅
- **Flutter analyze**: 0 errors, 0 warnings (only pre-existing `info`) ✅
- **Backend tests**: 21/21 pass (pnl_hardening + swap + sell) ✅
- **API verification**: `performance_value` returns correct monetary series (starts at 0, evolves in €) ✅
