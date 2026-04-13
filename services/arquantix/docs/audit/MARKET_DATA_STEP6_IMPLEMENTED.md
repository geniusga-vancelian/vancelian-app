# Market Data Step 6 – Implemented

**Date:** 2026-02-18  
**Scope:** 1-hour candles for Binance crypto instruments only. No other timeframes, no Yahoo changes, no modification of existing 5m behavior.

---

## Files created

| File | Description |
|------|-------------|
| `api/alembic/versions/017_add_market_data_bars_1h.py` | Migration: table `market_data_bars_1h`. |
| `api/services/market_data/bars_1h_repo.py` | Repository: `get_bars_1h`, `upsert_bar_1h`. |
| `api/services/market_data/ingestion_binance_candles_1h.py` | Ingestion: load Binance instruments, fetch 1h klines, upsert; commit once per cycle. |
| `api/scripts/run_candles_1h_ingestion.py` | Script entrypoint for 1h candle ingestion (optional `--limit`). |
| `docs/audit/MARKET_DATA_STEP6_IMPLEMENTED.md` | This note. |

---

## Files modified

| File | Change |
|------|--------|
| `api/database.py` | Added model `MarketDataBar1h`. |
| `api/services/market_data/binance_client.py` | Added `fetch_klines_1h(symbol, limit=500, start_time_ms=..., end_time_ms=...)`. |
| `api/services/market_data/routes.py` | Added `GET /api/market-data/candles/1h`. |

---

## Schema summary: `market_data_bars_1h`

| Column | Type | Nullable | Notes |
|--------|------|----------|--------|
| instrument_id | integer | NOT NULL | PK, FK → market_data_instruments.id (CASCADE) |
| open_time | timestamptz | NOT NULL | PK |
| open | numeric(20,8) | NOT NULL | |
| high | numeric(20,8) | NOT NULL | |
| low | numeric(20,8) | NOT NULL | |
| close | numeric(20,8) | NOT NULL | |
| volume | numeric(20,8) | NOT NULL | |
| source | varchar(50) | NOT NULL | default 'binance' |
| updated_at | timestamptz | NOT NULL | server default now() |

- Primary key: `(instrument_id, open_time)`.
- Indexes: `instrument_id`, `open_time`.

---

## Ingestion flow

1. **Script:** `python scripts/run_candles_1h_ingestion.py [--limit N]` (from `api/`).
2. **Ingestion:** Load instruments with `provider=binance`, `is_active=true`; for each, call `fetch_klines_1h(provider_symbol, limit)` (Binance REST `/api/v3/klines?interval=1h`); for each candle, `upsert_bar_1h(...)`; single `commit()` at the end.
3. **Client:** `fetch_klines_1h` returns normalized list of `{ open_time, open, high, low, close, volume }`.

---

## REST endpoint: GET /api/market-data/candles/1h

- **Query params:** `symbol` (e.g. BTCUSDT) or `instrument_id` (exactly one required). Optional: `start_time`, `end_time` (ISO 8601), `limit` (default 300, max 500).
- **Validation:** 400 if both `symbol` and `instrument_id` missing, or both provided. 400 if `start_time`/`end_time` invalid. Empty list if instrument not found or no bars.
- **Response:** `{ "candles": [ { "instrument_id", "symbol", "open_time", "open", "high", "low", "close", "volume" } ] }` (same shape as 5m).

---

## Operational notes

- **Run 1h ingestion:** From `api/`: `python scripts/run_candles_1h_ingestion.py` or `python scripts/run_candles_1h_ingestion.py --limit 300`.
- **When:** Manual backfill or cron (e.g. every hour). Not started from FastAPI.
- **Instruments:** Only `provider=binance`, `is_active=true`, non-empty `provider_symbol`.
- **Limit:** Up to 500 klines per symbol per run (default). Use `--limit` to change (max 1000).
- **Migration:** Apply revision 017 before first run: `alembic upgrade head` from `api/`.

---

## Intentionally not implemented

- Other timeframes (1m, 15m, 4h, 1d, 1w).
- Generic multi-timeframe abstraction.
- WebSocket candle streaming.
- Yahoo or other providers for 1h.
- FastAPI startup ingestion.
- Changes to 5m candle implementation.
