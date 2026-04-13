# Market Data Step 8 – Implemented

**Date:** 2026-02-18  
**Scope:** REST endpoint for 24h top movers (top gainers, top losers, top volume) using only existing persisted data. No schema, ingestion, or WebSocket changes.

---

## Endpoint

**GET** `/api/market-data/top-movers`

Returns three ranked lists for market overview sections.

---

## Query params

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `limit`   | int    | No       | Max size of each list (default 10, max 50). Applied independently to gainers, losers, volume. |
| `symbols` | string | No       | Comma-separated provider symbols (e.g. `BTCUSDT,ETHUSDT`). If provided, rankings are restricted to this universe. If omitted, rankings are over all active Binance instruments that have a latest quote. |

**Validation:** 400 if `limit` &lt; 1 or &gt; 50. Optional `symbols` are normalized (strip, uppercase).

---

## Response format

```json
{
  "top_gainers": [
    {
      "instrument_id": 1,
      "symbol": "BTCUSDT",
      "price": 68124.32,
      "change_24h_abs": 1245.12,
      "change_24h_pct": 1.86,
      "volume_24h": 12345.67,
      "sparkline_24h": [66879.2, 66910.4, 66888.1]
    }
  ],
  "top_losers": [ ... ],
  "top_volume": [ ... ]
}
```

Each item has the same shape as a market summary (price, change_24h_abs, change_24h_pct, volume_24h, sparkline_24h). The three arrays are always present; they may be empty.

---

## Ranking logic

- **top_gainers:** Sort by `change_24h_pct` descending. Exclude instruments where `change_24h_pct` is null. Take first `limit`.
- **top_losers:** Sort by `change_24h_pct` ascending. Exclude instruments where `change_24h_pct` is null. Take first `limit`.
- **top_volume:** Sort by `volume_24h` descending. Include instruments with zero volume if needed to fill. Take first `limit`.

An instrument can appear in more than one list. `limit` is applied to each list separately.

---

## Computation

Eligible instruments:

- **If `symbols` is provided:** Resolve to instrument IDs (via `MarketDataInstrument.provider_symbol`). Only instruments with a latest quote are included (handled inside `get_market_summaries`).
- **If `symbols` is omitted:** All instruments with `provider=binance`, `is_active=true`, and a row in `market_data_latest_quotes`.

For each eligible instrument, summary is computed by `get_market_summaries` (same as market-summary endpoint): latest quote + 5m candles over last 24h → price, reference_price_24h, change_24h_abs, change_24h_pct, volume_24h, sparkline_24h. Instruments without a latest quote are skipped.

---

## Edge cases

- **No data:** All three arrays are empty.
- **No instruments with `change_24h_pct`:** top_gainers and top_losers are []; top_volume may still have data.
- **`symbols` with no matching instruments or no quotes:** All three arrays empty.
- **Reference price zero in 24h:** change_24h_pct is null; instrument excluded from gainers/losers but can appear in top_volume.

---

## Files created

| File | Description |
|------|-------------|
| `api/services/market_data/top_movers_repo.py` | `_eligible_binance_instrument_ids(session)`, `get_top_movers(session, limit=10, provider_symbols=None)`; reuses `get_market_summaries`. |
| `docs/audit/MARKET_DATA_STEP8_IMPLEMENTED.md` | This document. |

---

## Files modified

| File | Change |
|------|--------|
| `api/services/market_data/routes.py` | Import `get_top_movers`; added `GET /api/market-data/top-movers` with `limit` and optional `symbols`, returns `get_top_movers(db, ...)`. |

---

## Known V1 limitations

- No caching; every request recomputes summaries and rankings.
- Universe when `symbols` is omitted is “Binance + active + has quote”; no other providers or filters.
- Same 24h window and 5m-based logic as market-summary (no custom period).
- An instrument with quote but no 5m data has change_24h_pct null so it never appears in gainers/losers; it can still appear in top_volume with volume_24h=0.
