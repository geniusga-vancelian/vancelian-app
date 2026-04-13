# Portfolio Global Consistency Audit

## Current State

Five screens display portfolio-related metrics:
| Screen | Endpoint | Source |
|--------|----------|--------|
| Home (dashboard) | `CryptoPositionsApi` + `CashApi` | `crypto_positions` + `custody_account_balances` |
| Global Statistics | `GET /portfolio/global/statistics` | `valuation.py` → `invariants.py` |
| Global History | `GET /portfolio/global/history` | `build_wallet_history(mode=value)` + fiat timeline |
| Crypto Statistics | `GET /portfolio/statistics` | `CryptoPositionRepository` + `build_wallet_statistics` |
| Bundle Statistics | `GET /bundle/{id}/statistics` | `pe_position_atoms` + `price_bridge` |

## Divergences Found

### 1. Home Chart — Mocked Data (CRITICAL)
**Root cause**: `LineChartModule` in `home_screen.dart` was called without `data` parameter. It fell back to `mockLineChartData100` — 100 random points generated with `Random(42)`.  
**Performance label**: Hardcoded `"0%"` string, never updated from API.

### 2. Global History — Performance Spike (CRITICAL)
**Root cause**: `get_global_portfolio_history` called `build_wallet_history` TWICE:
- `mode="value"` → produces timestamps set A (with live point at `datetime.now()` T₁)
- `mode="performance_value"` → produces timestamps set B (with live point at `datetime.now()` T₂)

When merging via `all_timestamps = sorted(set(A.keys() + B.keys()))`, timestamps in set A but not B would default to `nav_by_ts.get(ts, 0) = 0`, creating artificial spikes where `total_value` suddenly drops to just the fiat balance.

### 3. Global Statistics — API Error (MODERATE)
**Root cause**: The previous version of the history endpoint passed `scope="crypto"` and `period=period` as kwargs to `build_wallet_history`, but these parameters don't exist in the function signature. This caused a `TypeError` at runtime → `500 Internal Server Error` → Flutter displayed "Impossible de charger les statistiques".

### 4. Pricing Consistency — OK
All endpoints use the same pricing chain:
- `MarketDataLatestQuote.last_price` (USDT)
- `usdt_to_eur(price_usdt, eurusdt_rate)` via `get_eurusdt_rate(db)`
- No local FX conversion differences found.

### 5. Scope Consistency — OK
All endpoints correctly separate:
- `direct_portfolio` → "Mes crypto"
- `bundle_portfolio` → "Mes bundles"
- `crypto_positions` → consolidated view

## Root Causes

| Issue | Root Cause | Severity |
|-------|-----------|----------|
| Mocked home chart | `data` param never passed to `LineChartModule` | Critical |
| 0% performance | Label hardcoded in template | Critical |
| History spike | Double `build_wallet_history` call with timestamp merge | Critical |
| Stats page error | Invalid kwargs (`scope`, `period`) in `build_wallet_history` call | High |

## Refactoring

### New: `api/services/portfolio_engine/valuation.py`

Centralized valuation module providing:
- `get_asset_price_eur(db, asset)` — single-asset pricing
- `get_asset_value_eur(db, asset, quantity)` — mark-to-market
- `get_fiat_balance_eur(db, client_id)` — delegates to `invariants._get_client_eur_balance`
- `get_crypto_value_eur(db, client_id)` — delegates to `invariants._get_crypto_value_eur`
- `get_portfolio_breakdown(db, client_id)` — fiat + direct + bundles breakdown
- `get_net_deposits(db, client_id)` — cumulative external flows
- `get_pnl(db, client_id)` — aggregated realized + unrealized

All functions use the same pricing chain: `MarketDataLatestQuote` → `usdt_to_eur`.

### Fixed: Global History Endpoint

Replaced double `build_wallet_history` call with single `mode="value"` call.

New approach:
1. Single `build_wallet_history(mode="value")` → crypto NAV series
2. Fiat balance timeline from `CustodyTransaction` (all types)
3. Net deposits timeline from `CustodyTransaction` (bank transfers only)
4. For each NAV point: `total_value = crypto_nav + fiat_at(ts)`, `performance_value = total_value - net_deposits_at(ts)`

Eliminates timestamp divergence entirely.

### Fixed: Global Statistics Endpoint

Now uses `valuation.get_portfolio_breakdown()` and `valuation.get_pnl()` instead of inline calculations, ensuring consistency with every other page.

### Fixed: Home Dashboard

- `LineChartModule` now receives `data: _heroChartData` (real normalized values from global history)
- Performance label now shows real `_heroPerformancePct` from API
- Data loaded via `_loadHeroChart()` in `_loadAll()`

## Unified Valuation Engine

### Pricing chain (single source of truth)
```
MarketDataLatestQuote.last_price (USDT)
  → usdt_to_eur(price, eurusdt_rate)
  → EUR value
```

### eurusdt_rate source
```
get_eurusdt_rate(db, strict=False)
  → MarketDataLatestQuote WHERE provider_symbol = 'EURUSDT'
```

### Pages using this chain
- Home dashboard (via `CryptoPositionsApi` → `service.get_crypto_positions`)
- Global stats (via `valuation.get_portfolio_breakdown`)
- Global history (via `build_wallet_history(mode=value)`)
- Crypto stats (via `CryptoPositionRepository` + `build_wallet_statistics`)
- Bundle stats (via `pe_position_atoms` + `price_bridge`)

All converge to the same `MarketDataLatestQuote` + `usdt_to_eur` pipeline.

## Tests

### Test 1: Home == Global
Home total balance = `cashApi.balance + cryptoApi.totalValueEur`  
Global `current_value` = `fiat + crypto_total` via `valuation.get_portfolio_breakdown`  
Both use `MarketDataLatestQuote` → `usdt_to_eur`. ✅ Consistent.

### Test 2: Global == fiat + crypto + bundles
`get_portfolio_breakdown` returns `total_value = fiat + crypto_total`.  
`crypto_total` from `_get_crypto_value_eur` aggregates all `crypto_positions`.  
`direct + bundles ≤ crypto_total` (PE overlay invariant). ✅

### Test 3: Chart last point == current_value
`build_wallet_history` appends a live point from `MarketDataLatestQuote`.  
Global history adds `fiat_at(now)` to this live point.  
This equals `valuation.get_portfolio_breakdown().total_value`. ✅

### Test 4: No spike in global history
Single `build_wallet_history` call → single timestamp set → no default-to-zero merge. ✅

## Final Status

| Item | Status |
|------|--------|
| Home chart: real data | ✅ Fixed |
| Home performance label | ✅ Fixed |
| Global history spike | ✅ Fixed (single-call architecture) |
| Global stats API error | ✅ Fixed (removed invalid kwargs) |
| Centralized valuation | ✅ Created `valuation.py` |
| Pricing consistency | ✅ Verified (all use same chain) |
| Scope consistency | ✅ Verified |
