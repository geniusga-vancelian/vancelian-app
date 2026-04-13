# Market Data Step 7 – Implemented

**Date:** 2026-02-18  
**Scope:** REST endpoint for market summary (price, 24h change, volume, sparkline) derived from latest quotes and 5m candles. No schema, ingestion, or WebSocket changes.

---

## Endpoint

**GET** `/api/market-data/market-summary`

Returns one summary per requested instrument for market list / watchlist UI.

---

## Query params

| Parameter        | Type   | Required | Description |
|------------------|--------|----------|-------------|
| `symbols`        | string | No*      | Comma-separated provider symbols (e.g. `BTCUSDT,ETHUSDT`). |
| `instrument_ids` | string | No*      | Comma-separated instrument IDs (e.g. `1,2,3`). |

\* At least one of `symbols` or `instrument_ids` must be provided. If both are provided, results are merged and deduplicated by `instrument_id`.

**Validation:** 400 if both are missing. 400 if any `instrument_ids` value is not an integer.

---

## Response format

```json
{
  "summaries": [
    {
      "instrument_id": 1,
      "symbol": "BTCUSDT",
      "price": 68124.32,
      "change_24h_abs": 1245.12,
      "change_24h_pct": 1.86,
      "volume_24h": 12345.67,
      "sparkline_24h": [66879.2, 66910.4, 66888.1, 67001.5]
    }
  ]
}
```

- `price`: from latest quote (`last_price`).
- `change_24h_abs`: current price minus oldest 5m close in the 24h window; `null` if no candles or reference is zero.
- `change_24h_pct`: `(price - reference) / reference * 100`; `null` if no candles or reference is zero.
- `volume_24h`: sum of 5m candle volumes in the last 24h; `0` if no candles.
- `sparkline_24h`: ordered list of 5m candle close values in the last 24h; `[]` if no candles.

---

## Computation rules

For each requested instrument (after resolving and deduplicating by `instrument_id`):

1. Load latest quote from `market_data_latest_quotes`. If none → **skip** the instrument (no entry in `summaries`).
2. Load 5m candles from `market_data_bars_5m` for the last 24 hours (window: `now_utc - 24h` to `now_utc`).
3. **If there are candles:**
   - `reference_price_24h` = close of the **oldest** candle in the window.
   - `change_24h_abs` = `price - reference_price_24h`.
   - `change_24h_pct` = `((price - reference_price_24h) / reference_price_24h) * 100`.
   - `volume_24h` = sum of candle volumes.
   - `sparkline_24h` = list of candle close values in time order.
4. **If there is a quote but no candles:**
   - `price` = from quote.
   - `change_24h_abs` = `null`, `change_24h_pct` = `null`, `volume_24h` = `0`, `sparkline_24h` = `[]`.

---

## Edge cases

- **No latest quote for instrument:** Instrument is omitted from `summaries`.
- **Quote exists, no 5m data in 24h:** Summary returned with `price`; change fields `null`; `volume_24h` 0; `sparkline_24h` [].
- **Reference price zero:** `change_24h_abs` and `change_24h_pct` set to `null` to avoid division by zero.
- **Empty request (no instruments after resolve):** `summaries` = [].

---

## Files created

| File | Description |
|------|-------------|
| `api/services/market_data/market_summary_repo.py` | `get_market_summaries(session, instrument_ids, provider_symbols)`; resolves instruments, loads quotes + 5m bars, computes summary per instrument. |
| `docs/audit/MARKET_DATA_STEP7_IMPLEMENTED.md` | This document. |

---

## Files modified

| File | Change |
|------|--------|
| `api/services/market_data/routes.py` | Added `GET /api/market-data/market-summary`; parses `symbols` / `instrument_ids`, calls `get_market_summaries`, returns `{"summaries": ...}`. |

---

## Known limitations (V1)

- **24h window** is fixed (last 24 hours from request time). No timezone or custom range parameter.
- **Sparkline** can contain up to ~288 points (5m bars in 24h). No downsampling; frontend may need to sample for display.
- **Performance:** One query for quotes, one per instrument for 5m bars. Acceptable for moderate watchlist sizes; for many instruments consider batching or caching in a later version.
- No Redis or cache; every request hits the database.
