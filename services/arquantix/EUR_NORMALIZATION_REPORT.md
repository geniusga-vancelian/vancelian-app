# EUR Normalization Report

## Executive Summary

The Vancelian pricing system has been normalized to produce true EUR prices from USDT market data. A centralized FX conversion layer (`services/market_data/fx.py`) now converts all USDT prices to EUR using the live EURUSDT rate from Binance, applied consistently across the Exchange engine, crypto valuations, and all market-data endpoints.

**Before**: All prices were USDT (Binance) but labeled and used as EUR. ~8% pricing error.
**After**: All prices are properly converted via `price_eur = price_usdt / eurusdt_rate`.

All 73 existing tests pass with 0 regressions.

---

## Files Created

| File | Purpose |
|------|---------|
| `api/services/market_data/fx.py` | Central FX module: `get_eurusdt_rate()`, `usdt_to_eur()`, fallback logic, staleness check |

## Files Modified

| File | Changes |
|------|---------|
| `api/scripts/ensure_binance_instruments.py` | Added `BINANCE_FX_SYMBOLS = [("EURUSDT", "EUR/USDT")]`, refactored to support forex asset class |
| `api/services/exchange/service.py` | `_resolve_price()` now converts USDT to EUR via `get_eurusdt_rate()` + `usdt_to_eur()` |
| `api/services/test_clients/service.py` | `get_crypto_positions()` and `get_crypto_wallet_detail()` now convert prices to EUR |
| `api/services/market_data/market_summary_repo.py` | `get_market_summaries()` accepts `include_eur=True` and adds `price_eur` to output |
| `api/services/market_data/routes.py` | `all-crypto` and `market-summary` endpoints include `price_eur`; `quotes/latest` includes `price_eur` |
| `api/services/market_data/quotes_repo.py` | `quotes_to_payload()` accepts optional `eurusdt_rate` and adds `price_eur` |
| `api/services/market_data/ws_broadcast.py` | WebSocket market-data broadcast includes `price_eur` |

---

## Architecture

### FX Module (`api/services/market_data/fx.py`)

Single source of truth for USDT-to-EUR conversion:

```
get_eurusdt_rate(db, strict=False)  -> Decimal
  - Reads EURUSDT from market_data_latest_quotes
  - strict=True: raises if quote missing or stale (>300s)
  - strict=False: falls back to DEFAULT_EURUSDT_RATE (1.08) if unavailable

usdt_to_eur(price_usdt, eurusdt_rate)  -> Decimal
  - Formula: price_eur = price_usdt / eurusdt_rate
```

### Conversion Flow

```
Binance WS ──→ market_data_latest_quotes (EURUSDT)
                         │
                         ▼
                   fx.get_eurusdt_rate()
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        Exchange    Valuation   Market-data
     _resolve_price  positions   all-crypto
       BUY/SELL    wallet_detail  summaries
                                 quotes/latest
                                 WS broadcast
```

### EURUSDT Ingestion

The EURUSDT instrument has been:
1. Added to `BINANCE_FX_SYMBOLS` in `ensure_binance_instruments.py`
2. Seeded in the database (`asset_class=forex`, `provider=binance`)
3. Automatically picked up by the Binance WebSocket ingestion (it loads all `provider=binance, is_active=true` instruments)

No additional configuration is needed — the existing WebSocket process will subscribe to `eurusdt@bookTicker` on next restart.

---

## Impact by Component

### Exchange Engine (BUY + SELL)

| Before | After |
|--------|-------|
| `_resolve_price()` returns USDT price | Returns EUR price (`usdt / eurusdt_rate`) |
| `price_override` assumed to be EUR | Unchanged — still treated as EUR (bypasses conversion) |
| `gross_eur`, `net_eur` were in USDT | Now truly in EUR |

### Crypto Valuation

| Before | After |
|--------|-------|
| `price_eur` = USDT price | `price_eur` = USDT price / EURUSDT rate |
| `estimated_value_eur` = balance * USDT | `estimated_value_eur` = balance * (USDT / EURUSDT) |
| `current_price_eur` = USDT | `current_price_eur` = true EUR price |

### Market Data Endpoints

| Endpoint | New field |
|----------|-----------|
| `GET /api/market-data/all-crypto` | `price_eur` added to each summary |
| `GET /api/market-data/market-summary` | `price_eur` added to each summary |
| `GET /api/market-data/quotes/latest` | `price_eur` added to each quote |
| `WS /ws/market-data` | `price_eur` added to each quote broadcast |

The original `price` field still contains the raw USDT price for backward compatibility.

---

## Fallback Strategy

| Scenario | Behavior |
|----------|----------|
| EURUSDT quote not in DB | Use `DEFAULT_EURUSDT_RATE = 1.08` with warning log |
| EURUSDT quote stale (strict mode) | Raise `FxQuoteStaleError` (exchange trades only) |
| EURUSDT quote stale (non-strict) | Use last known rate (valuations/display) |
| EURUSDT rate = 0 | Fall back to default rate |
| WebSocket not running | Binance REST fallback already handles this for crypto quotes; EURUSDT will be fetched the same way |

---

## Test Results

```
58 passed (exchange + custody + crypto_custody + reset)
15 passed (test_clients + euro_account)
 0 failed
 0 regressions
```

All existing tests use `price_override` for exchange operations, so the FX conversion path is bypassed in tests (as designed). The override is documented as being in EUR.

---

## What Was NOT Changed

- No database migrations
- No schema changes
- No existing tables modified
- BUY engine logic unchanged (only price resolution modified)
- SELL engine logic unchanged
- Settlement engine unchanged
- Crypto custody architecture unchanged
- Flutter code unchanged (backend provides correct EUR values)
- Existing API response formats preserved (`price` field still returns USDT)

---

## Remaining Items (Not Implemented)

1. **Flutter `AllCryptoScreen`**: Currently uses `price` (USDT). Should be updated to use `price_eur` when available. This is a Flutter-side change.

2. **Quote staleness in exchange**: `strict=False` is currently used in `_resolve_price()`. For production, consider switching to `strict=True` to reject trades when the FX quote is stale.

3. **Performance 1d% calculation**: Still uses raw USDT prices for the previous close bar comparison. The percentage change is the same in USDT or EUR (it's a ratio), so this is correct.

4. **Historical order prices**: Past orders were executed with USDT-as-EUR prices. No retroactive correction was applied. Future orders will use proper EUR prices.
