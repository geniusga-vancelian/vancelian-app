# Market Data Step 9 – Implemented

**Date:** 2026-02-18  
**Scope:** WebSocket-based Binance latest quote ingestion (bookTicker stream). Replaces REST polling for real-time quotes; REST polling script left in place as fallback. No schema, REST API, or frontend WebSocket changes.

---

## Files created

| File | Description |
|------|-------------|
| `api/services/market_data/binance_ws_ingestion.py` | Async WebSocket client: load Binance instruments, subscribe to combined bookTicker stream, parse events, batch upsert via `quotes_repo`, reconnect with backoff. |
| `api/scripts/run_binance_ws_ingestion.py` | Entrypoint: runs `run_ws_ingestion()` until SIGINT/SIGTERM. |
| `docs/audit/MARKET_DATA_STEP9_IMPLEMENTED.md` | This document. |

---

## Files modified

| File | Change |
|------|--------|
| `api/requirements.txt` | Added `websockets>=12.0`. |
| `api/services/market_data/config.py` | Added `BINANCE_WS_BASE_URL`, `BINANCE_WS_INGESTION_COMMIT_BATCH_SIZE`, `BINANCE_WS_INGESTION_COMMIT_INTERVAL_SEC`, `BINANCE_WS_RECONNECT_BASE_DELAY_SEC`, `BINANCE_WS_RECONNECT_MAX_DELAY_SEC`. |

---

## Stream choice

- **Binance Spot combined stream:** `bookTicker` per symbol.
- **URL pattern:** `wss://stream.binance.com:9443/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker/...`
- **Event format:** `{"stream":"btcusdt@bookTicker","data":{...}}` with `data.b` (best bid), `data.a` (best ask), `data.s` (symbol). No last traded price in bookTicker; last_price is computed as midpoint of bid and ask.

---

## Symbol normalization

- **DB / persistence:** `provider_symbol` stored in **uppercase** (e.g. BTCUSDT).
- **Subscription:** Stream names use **lowercase** (e.g. `btcusdt@bookTicker`) per Binance API.
- **Mapping:** Instruments loaded with `provider_symbol` stripped and uppercased; stream list built with `.lower()` for the URL.

---

## Data mapping (bookTicker → latest quote)

| Field | Source |
|-------|--------|
| provider | `"binance"` |
| provider_symbol | Binance symbol in uppercase (e.g. from `data.s` or stream name) |
| bid_price | `data.b` |
| ask_price | `data.a` |
| last_price | `(bid + ask) / 2` |
| volume | not in bookTicker → `None` |
| quote_time | `data.E` or `data.e` (event time ms) if present, else current UTC time |

Missing or invalid fields are handled safely (skip or default).

---

## Commit batching

- **Strategy:** Commit when either (1) pending updates count ≥ `BINANCE_WS_INGESTION_COMMIT_BATCH_SIZE` (default 20), or (2) time since last commit ≥ `BINANCE_WS_INGESTION_COMMIT_INTERVAL_SEC` (default 2.0).
- **Implementation:** Pending updates stored in a dict (one entry per symbol, last update wins). When a flush is triggered, a **copy** of the pending dict is passed to a sync `_flush_pending` run in a thread executor; session is opened, all pending rows upserted, commit, session closed. Only the flushed keys are removed from pending so updates received during the flush are kept.
- **On error:** Rollback, log, continue; next batch will retry.

---

## Reconnect behavior

- **When:** Connection closes (normal, 24h limit, or network error), parse error on a message does not disconnect (message skipped).
- **Backoff:** Start at `BINANCE_WS_RECONNECT_BASE_DELAY_SEC` (default 1.0), double after each disconnect, cap at `BINANCE_WS_RECONNECT_MAX_DELAY_SEC` (default 60.0). Reset to base delay after a successful connection.
- **Instrument list:** Loaded once at startup. On reconnect the same list is used; restart the script to pick up new/removed instruments.

---

## Ping / pong

- The `websockets` library is used with `ping_interval=20`, `ping_timeout=20` so the client sends pings and expects pongs; the connection is closed if the server does not respond.

---

## Operational run instructions

- **From api/:** `python scripts/run_binance_ws_ingestion.py`
- **Behavior:** Loads Binance instruments from DB, opens one combined WebSocket connection, processes bookTicker events, batch-commits to `market_data_latest_quotes`, reconnects with backoff on disconnect. Runs until SIGINT/SIGTERM (where supported).
- **Env (optional):** `BINANCE_WS_BASE_URL`, `BINANCE_WS_INGESTION_COMMIT_BATCH_SIZE`, `BINANCE_WS_INGESTION_COMMIT_INTERVAL_SEC`, `BINANCE_WS_RECONNECT_BASE_DELAY_SEC`, `BINANCE_WS_RECONNECT_MAX_DELAY_SEC`.
- **Coexistence:** The REST polling script `run_binance_ingestion.py` is unchanged and can be used as a fallback; the WebSocket worker is the recommended path for latest quotes when available.

---

## Intentionally not implemented

- Integration into FastAPI startup (worker remains a separate process).
- WebSocket candle/kline ingestion.
- REST or frontend WebSocket changes.
- Redis or caching.
- Multi-connection sharding (one combined connection for V1).
- Reload of instrument list on reconnect (restart script to pick up changes).
