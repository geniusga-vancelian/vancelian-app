# Simulated Market Execution — Implementation Report

## Executive Summary

Simulated Market Execution v1 has been implemented for the Vancelian Exchange Engine. The system now supports realistic BUY/SELL execution using live bid/ask prices from Binance, with a configurable spread fallback, a 60-second freshness guard, and a dual-mode admin UI (Market Simulated / Manual Override).

**Key outcomes:**
- BUY executes at **ask price** (higher), SELL executes at **bid price** (lower)
- Quote freshness enforced: trades rejected if quote > 60 seconds old
- Manual price override remains fully functional for testing/debug
- All 15 existing exchange tests pass (zero regression)
- 11 new tests added and passing
- Admin UI updated with live price display and mode selector

---

## Files Modified

### Backend (API)

| File | Change |
|------|--------|
| `api/services/exchange/service.py` | Rewrote `_resolve_price()` with `side` param, bid/ask logic, freshness guard. Added `MarketQuoteStaleError`, `MAX_QUOTE_AGE_SECONDS`. |
| `api/services/exchange/models.py` | Added `spread_bps` column to `ExchangeFeeConfig` model. |
| `api/services/exchange/repository.py` | Added `get_active_spread_bps()`. Updated `upsert()` to accept `spread_bps`. |
| `api/services/exchange/router.py` | Added `MarketQuoteStaleError` to import and exception handling (HTTP 503). |
| `api/services/exchange/admin_router.py` | Enriched `/api/admin/exchange/context` with bid/ask/mid prices, spread_bps, quote_time, is_fresh. |

### Database

| File | Change |
|------|--------|
| `api/alembic/versions/066_add_spread_bps_to_exchange_fee_config.py` | New migration: adds `spread_bps INTEGER NOT NULL DEFAULT 50` to `exchange_fee_config`. |

### Frontend (Web)

| File | Change |
|------|--------|
| `web/src/app/admin/exchange-test/page.tsx` | Complete rewrite with dual mode (Market/Manual), live price panel, freshness indicator, smart execute button. |

### Tests

| File | Change |
|------|--------|
| `api/tests/test_simulated_market_execution.py` | New file: 11 tests covering all pricing scenarios. |

---

## Pricing Logic Changes

### Before

```
_resolve_price(db, asset, override_price) -> Decimal (EUR)
  if override_price → return it
  else → last_price (USDT) → convert to EUR
```

Both BUY and SELL used the same `last_price` (mid-price).

### After

```
_resolve_price(db, asset, override_price, side) -> Decimal (EUR)
  if override_price → return it (no freshness check)
  else:
    1. Load quote from market_data_latest_quotes
    2. Check freshness (quote_time must be < 60s old)
    3. If bid_price and ask_price available:
       BUY → use ask_price
       SELL → use bid_price
    4. Else (fallback):
       mid = last_price
       BUY → mid * (1 + spread_bps/20000)
       SELL → mid * (1 - spread_bps/20000)
    5. Convert USDT → EUR via existing FX module
```

### Method signature change

```python
# Before (static method)
@staticmethod
def _resolve_price(db, asset, override_price) -> Decimal

# After (instance method, accesses self._fee_repo for spread)
def _resolve_price(self, db, asset, override_price, side="buy") -> Decimal
```

---

## Spread Configuration Changes

### New column

`exchange_fee_config.spread_bps` — Integer, NOT NULL, default 50 (0.50%).

### Repository

`ExchangeFeeConfigRepository.get_active_spread_bps(db, asset)` — returns `spread_bps` for the asset, defaulting to 50 if no config exists.

### Usage

The spread is only used in the **fallback path** when `bid_price` or `ask_price` are NULL in the database. With the Binance `bookTicker` WebSocket running, real bid/ask are always available, so the spread is a safety net.

---

## Tick Freshness Guard

### Rule

- `quote_time` must exist (not NULL)
- `quote_time` must be within 60 seconds of current UTC time
- If stale → `MarketQuoteStaleError` raised → HTTP 503 returned

### Scope

- Applies to BUY and SELL in market mode (no override)
- Does **NOT** apply when `override_price` is provided (manual override bypasses freshness check intentionally, as it is operator-driven)

### Constant

```python
MAX_QUOTE_AGE_SECONDS = 60  # in service.py
```

---

## Admin UI Changes

### Mode selector

Two modes accessible via toggle buttons:

1. **Market Simulated** (default)
   - No price input field shown
   - Live bid/ask/mid prices displayed with auto-refresh (5s)
   - Quote freshness indicator (FRESH / STALE badge)
   - Execute button disabled when quote is stale
   - Payload sent without `price` field → backend uses market price

2. **Manual Override**
   - Price input field shown (same as before)
   - No freshness check on frontend
   - Payload sent with `price` field → backend uses override

### Live price panel

Displayed in Market Simulated mode:
- Bid price (EUR) — used for SELL
- Mid price (EUR)
- Ask price (EUR) — used for BUY
- Spread (bps and %)
- Fee (bps)
- Quote timestamp
- Freshness status with color coding

### Preview

Both BUY and SELL previews now work with either:
- Live ask/bid price (market mode)
- Manual price (override mode)

---

## Tests Added

### Unit tests (TestResolvePrice)

| Test | Validates |
|------|-----------|
| `test_buy_uses_ask_when_no_override` | BUY resolves to ask_price |
| `test_sell_uses_bid_when_no_override` | SELL resolves to bid_price |
| `test_buy_higher_than_sell` | ask > bid invariant |
| `test_fallback_spread_when_bid_ask_missing` | Simulated spread from last_price |
| `test_override_still_wins` | Override bypasses market price |
| `test_buy_rejected_when_quote_stale` | 120s-old quote → MarketQuoteStaleError |
| `test_sell_rejected_when_quote_stale` | 120s-old quote → MarketQuoteStaleError |
| `test_quote_missing_timestamp_rejected` | NULL quote_time → MarketQuoteStaleError |
| `test_override_allowed_even_when_stale` | Override works with stale quote |
| `test_eur_conversion_correct` | USDT→EUR conversion via FX rate |

### Integration tests (TestExchangeContext)

| Test | Validates |
|------|-----------|
| `test_context_returns_bid_ask_mid_spread` | Admin context endpoint returns price data |

### Regression

All 15 existing `test_exchange_engine.py` tests pass unchanged.

---

## Final Status

| Item | Status |
|------|--------|
| Migration 066 applied | Done |
| `_resolve_price()` updated | Done |
| `buy()` passes `side="buy"` | Done |
| `sell()` passes `side="sell"` | Done |
| Freshness guard (60s) | Done |
| `MarketQuoteStaleError` → HTTP 503 | Done |
| Admin context enriched | Done |
| Admin UI dual mode | Done |
| Tests (11 new, 15 existing) | All passing |
| Downstream impact | None (price stored in exchange_orders.price remains source of truth) |
