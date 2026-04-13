# Market Data Step 4 – Implemented

**Date:** 2026-02-18  
**Scope:** WebSocket endpoint that broadcasts latest market quotes to connected clients every 2 seconds. No ingestion changes, no schema changes, no OHLC.

---

## Endpoint

**WebSocket** `ws://<host>/ws/market-data?symbols=BTCUSDT,ETHUSDT`

- Path: `/ws/market-data`
- Subscription is via query parameter `symbols` only (no `instrument_ids` in this step).
- **Authentication:** None in V1. There is no existing WebSocket auth pattern in the codebase; auth is left for V2 and documented below.

---

## Subscription format

- **Query parameter:** `symbols` (required).
- **Value:** Comma-separated provider/market symbols (e.g. `BTCUSDT`, `ETHUSDT`).
- **Parsing:** Symbols are normalized (strip, uppercase) and deduplicated.
- **Validation:**
  - If `symbols` is missing or empty after parsing → connection is closed with code `4000` and reason: `Missing or empty query parameter: symbols (e.g. ?symbols=BTCUSDT,ETHUSDT)`.
  - Invalid query params result in the same close.

---

## Payload format

Every 2 seconds the server sends one JSON message:

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

- Same shape as the REST `GET /api/market-data/quotes/latest` response.
- If no quotes are found for the subscribed symbols, the server sends `{"quotes": []}` and **does not** close the connection.

---

## Error behavior

- **Missing/empty symbols:** Connection closed with WebSocket close code `4000` and reason describing the required `symbols` query parameter.
- **Server error during broadcast:** Connection closed with code `1011` (internal error), reason `Server error`; DB session is closed.
- **Client disconnect:** Loop exits, DB session closed in `finally`; no noisy logging.
- **Empty quote results:** Send `{"quotes": []}` and keep connection open.

---

## Implementation notes

- **Data access:** Reuses `quotes_repo.get_latest_quotes_by_provider_symbols` and `quotes_to_payload`. REST and WebSocket share the same payload building via `quotes_to_payload` in the repo.
- **Polling:** DB is polled every 2 seconds; no Redis, no in-memory pub/sub. Sync DB calls are run in a thread via `asyncio.to_thread` so the event loop is not blocked.
- **Lifecycle:** One DB session per connection; session is closed in `finally` on disconnect or error.
- **Registration:** WebSocket is registered in `main.py` and delegates to `services.market_data.ws_broadcast.handle_market_data_ws`.

---

## Files modified / created

| File | Change |
|------|--------|
| `api/services/market_data/quotes_repo.py` | Added `get_latest_quotes_by_provider_symbols`, `quotes_to_payload`. |
| `api/services/market_data/routes.py` | REST `/quotes/latest` now uses repo + `quotes_to_payload` (shared serialization). |
| `api/services/market_data/ws_broadcast.py` | **New.** Parse `symbols`, validate, loop: fetch quotes, send JSON every 2s. |
| `api/main.py` | Registered `GET /ws/market-data` → `handle_market_data_ws`. |
| `docs/audit/MARKET_DATA_STEP4_IMPLEMENTED.md` | This document. |

---

## Intentionally not implemented (V1)

- WebSocket authentication (to be added in V2).
- Subscription by `instrument_ids` (symbols only in this step).
- Redis or in-memory pub/sub.
- OHLC / klines.
- Changes to Binance ingestion or startup behavior.

---

## V2 suggestions

- **Auth:** Validate token (e.g. JWT) via query param or first message and close unauthenticated connections.
- **instrument_ids:** Optional support for `instrument_ids` in addition to `symbols`.
- **Rate / backpressure:** Optional per-connection or global rate limit to avoid abuse.
