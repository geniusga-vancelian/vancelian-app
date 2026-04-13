# Portfolio Scoped Wallet History & Statistics

## Executive Summary

`wallet_statistics` and `wallet_history` now accept optional `portfolio_scope` / `portfolio_id` parameters enabling per-portfolio computation of stats, PnL, and chart series.

Three scopes are supported:
- **direct** — non-bundle orders + direct portfolio atoms
- **bundle** — bundle orders for a specific portfolio_id + bundle atoms
- **global** — all orders + crypto_positions (backward compatible default)

All existing callers continue to work without changes (global scope by default).

## Current Global Limitation (before this patch)

Both services computed statistics and history from **all** `exchange_orders` for a client/asset, regardless of whether orders belonged to direct trades or bundle operations. `position_size` was always sourced from `crypto_positions` (the consolidated view). This made it impossible to display direct-only or bundle-only PnL/charts.

## Scoped Statistics Design

### `build_wallet_statistics` — new optional parameters

```python
portfolio_scope: Optional[str] = None   # "direct" | "bundle" | None
portfolio_id: Optional[str] = None       # required when scope="bundle"
```

### Order filtering (`_apply_scope_filter`)

| Scope | Filter |
|-------|--------|
| global / None | No filter (all orders) |
| direct | `NOT external_reference LIKE 'bundle-%'` |
| bundle | `metadata_->>'bundle_id' == portfolio_id` |

### Position size (`_get_scoped_position_size`)

| Scope | Source |
|-------|--------|
| global / None | `crypto_positions.balance` |
| direct | `pe_position_atoms` in client's `direct_portfolio` |
| bundle | `pe_position_atoms` in the specified `bundle_portfolio` |

### Computed metrics (all scoped)

- current_value, position_size, avg_buy_price (PRU), current_price
- unrealized_pnl, realized_pnl, total_pnl
- trade_count, buy_count, sell_count, total_bought, total_sold
- volatility_30d, max_drawdown, break_even_distance_pct, portfolio_weight
- Response includes `"scope"` field for traceability

## Scoped Wallet History Design

### `build_wallet_history` — new optional parameters

```python
portfolio_scope: Optional[str] = None
portfolio_id: Optional[str] = None
```

### Order filtering (`_apply_history_scope_filter`)

Same logic as statistics — orders are filtered before position reconstruction, so the reconstructed positions and valuations naturally reflect only the specified scope.

### Result

Correctly scoped time-series for both `value` and `performance_value` modes.

## Direct Portfolio Handling

- Orders: all non-bundle orders (`external_reference` not starting with `bundle-`)
- Position: from `pe_position_atoms` attached to the client's `direct_portfolio`
- Covers historical direct orders (before overlay) by exclusion pattern

## Bundle Portfolio Handling

- Orders: only those tagged with `metadata_->>'bundle_id' == portfolio_id`
- Position: from `pe_position_atoms` attached to the specified bundle portfolio
- Correctly captures funding BUY (EUR→USDC), allocation SWAPs, and any subsequent operations

## Global Compatibility

- Default behavior (no scope parameters) is **100% backward compatible**
- All existing endpoints, callers, and Flutter screens work unchanged
- Global scope still uses `crypto_positions` for position_size and all orders for stats

## Endpoints Updated

### Modified existing endpoints (backward compatible)

| Endpoint | New query params |
|----------|-----------------|
| `GET /api/app/wallet/history` | `portfolio_scope`, `portfolio_id` |
| `GET /api/app/wallet/statistics/{asset}` | `portfolio_scope`, `portfolio_id` |

### New bundle-specific endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/app/bundle/{portfolio_id}/statistics` | Per-asset statistics for all assets in a bundle |
| `GET /api/app/bundle/{portfolio_id}/history` | Value/performance time-series for a bundle |

### Next.js proxy routes updated/created

| Route | Target |
|-------|--------|
| `wallet/history/route.ts` | Passes `portfolio_scope`, `portfolio_id` |
| `wallet/statistics/[asset]/route.ts` | Passes `portfolio_scope`, `portfolio_id` |
| `bundle/[portfolioId]/statistics/route.ts` | **New** |
| `bundle/[portfolioId]/history/route.ts` | **New** |

### Flutter Config URLs added

- `walletHistoryUrl` — accepts `portfolioScope`, `portfolioId`
- `walletStatisticsUrl` — accepts `portfolioScope`, `portfolioId`
- `bundleHistoryUrl(portfolioId, period, ...)` — **New**
- `bundleStatisticsUrl(portfolioId)` — **New**

## Flutter UI Changes

### Mes crypto (CryptoWalletDetailScreen)

- Hero sparkline: `portfolioScope: 'direct'` → shows direct-only PnL chart
- Statistics button: opens `WalletStatisticsScreen(portfolioScope: 'direct')` → direct-only stats

### Mes bundles (BundleWalletDetailScreen)

- Hero sparkline: `fetchBundleHistory(portfolioId)` → shows bundle-specific PnL chart
- Chart refreshes after new investment

### WalletStatisticsScreen

- Accepts optional `portfolioScope` and `portfolioId` parameters
- Passes them through to both `fetchStatistics()` and `fetchHistory()` calls

### AllCryptoPositionsScreen

- Hero sparkline remains global (`scope: 'crypto'`) — matches the hero total (direct + bundles)

## Tests (validation scenarios)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | BUY spot direct → direct stats | Direct stats updated, bundle stats unchanged |
| 2 | Invest bundle → bundle stats | Bundle stats updated, direct stats unchanged |
| 3 | SELL spot direct → realized direct | Realized PnL reflected in direct scope only |
| 4 | SELL/swap within bundle → bundle stats | Bundle stats updated correctly |
| 5 | wallet_history direct scoped | Does not include bundle orders |
| 6 | wallet_history bundle scoped | Does not include direct orders |
| 7 | Global scoped = direct + bundles | Sum of scoped values matches global |
| 8 | PRU/cost basis direct after backfill | Matches WAC from non-bundle buy orders |
| 9 | PRU/cost basis bundle correct | Matches bundle swap execution prices |
| 10 | Non-regression global stats/charts | Unchanged behavior when no scope parameter |

## Final Status

**IMPLEMENTED** — All scoping is in place across backend services, API endpoints, Next.js proxies, and Flutter UI. The implementation is incremental and fully backward compatible.

### Files modified

**Backend:**
- `api/services/wallet_statistics/service.py` — scoped stats with `_apply_scope_filter`, `_get_scoped_position_size`
- `api/services/wallet_history/service.py` — scoped history with `_apply_history_scope_filter`
- `api/services/test_clients/router.py` — scope query params on existing endpoints + new bundle endpoints

**Next.js proxies:**
- `web/src/app/api/mobile/flutter/wallet/history/route.ts` — passes scope params
- `web/src/app/api/mobile/flutter/wallet/statistics/[asset]/route.ts` — passes scope params
- `web/src/app/api/mobile/flutter/bundle/[portfolioId]/statistics/route.ts` — **new**
- `web/src/app/api/mobile/flutter/bundle/[portfolioId]/history/route.ts` — **new**

**Flutter:**
- `mobile/lib/core/config.dart` — new URL helpers with scope params
- `mobile/lib/features/wallet/data/wallet_history_api.dart` — scope params + `fetchBundleHistory`
- `mobile/lib/features/wallet/data/wallet_statistics_api.dart` — scope params
- `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` — direct scope
- `mobile/lib/features/wallet/presentation/screens/wallet_statistics_screen.dart` — accepts scope
- `mobile/lib/features/wallet/presentation/screens/bundle_wallet_detail_screen.dart` — bundle chart
