# Market Data Step 3 – Implemented

**Date:** 2026-02-18  
**Scope:** REST endpoint exposing latest market quotes from `market_data_latest_quotes`. No WebSocket, no ingestion changes, no OHLC.

---

## Endpoint

**GET** `/api/market-data/quotes/latest`

Returns the latest stored quotes for the requested instruments. Protected by existing JWT auth (same as other market-data routes).

---

## Parameters

| Parameter        | Type   | Required | Description |
|------------------|--------|----------|-------------|
| `symbols`        | string | No*      | Comma-separated provider/market symbols (e.g. `BTCUSDT`, `ETHUSDT`). |
| `instrument_ids` | string | No*      | Comma-separated instrument IDs (e.g. `1,2,3`). |

\* At least one of `symbols` or `instrument_ids` must be provided. If both are present, results are merged and deduplicated by `instrument_id`.

---

## Validation

- **400 Bad Request** if both `symbols` and `instrument_ids` are missing or empty after parsing.
- **400 Bad Request** if `instrument_ids` contains a non-integer value.
- If no quotes are found for the requested symbols/IDs, the response is `{"quotes": []}` (empty list, not an error).

---

## Response format

```json
{
  "quotes": [
    {
      "instrument_id": 1,
      "symbol": "BTCUSDT",
      "price": 68124.32,
      "bid_price": 68124.10,
      "ask_price": 68124.50,
      "volume": 123456,
      "quote_time": "2026-02-18T12:32:12Z",
      "updated_at": "2026-02-18T12:32:13Z"
    }
  ]
}
```

- `symbol`: provider/market symbol from the quote (e.g. BTCUSDT).
- `price`: last traded price (`last_price` in DB).
- `bid_price`, `ask_price`, `volume`: nullable; omitted as `null` when not set.
- `quote_time`, `updated_at`: ISO 8601 with timezone, or `null` when not set.

---

## Example

```http
GET /api/market-data/quotes/latest?symbols=BTCUSDT,ETHUSDT
Authorization: Bearer <token>
```

```http
GET /api/market-data/quotes/latest?instrument_ids=1,2
Authorization: Bearer <token>
```

---

## Files modified

- **`api/services/market_data/routes.py`**: Added `GET /quotes/latest` handler; uses `quotes_repo.get_latest_quotes_by_instrument_ids` for `instrument_ids` and a direct query on `MarketDataLatestQuote.provider_symbol` for `symbols`; returns the structure above.

---

## Intentionally not implemented

- WebSocket.
- Changes to Binance ingestion or scripts.
- OHLC / klines endpoints.
