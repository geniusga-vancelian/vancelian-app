# Market Data Step 5 – Implemented

**Date:** 2026-02-18  
**Scope:** Intraday 5-minute candles for Binance crypto instruments only. No other timeframes, no Yahoo changes, no WebSocket candle streaming.

---

## Files created

| File | Description |
|------|-------------|
| `api/alembic/versions/016_add_market_data_bars_5m.py` | Migration: table `market_data_bars_5m`. |
| `api/services/market_data/bars_5m_repo.py` | Repository: `get_bars_5m`, `upsert_bar_5m`. |
| `api/services/market_data/ingestion_binance_candles_5m.py` | Ingestion: load Binance instruments, fetch 5m klines, upsert; commit once per cycle. |
| `api/scripts/run_candles_5m_ingestion.py` | Script entrypoint for 5m candle ingestion (optional `--limit`). |
| `docs/audit/MARKET_DATA_STEP5_IMPLEMENTED.md` | This note. |

---

## Files modified

| File | Change |
|------|--------|
| `api/database.py` | Added model `MarketDataBar5m`. |
| `api/services/market_data/binance_client.py` | Added `fetch_klines_5m(symbol, limit=500, start_time_ms=..., end_time_ms=...)`. |
| `api/services/market_data/routes.py` | Added `GET /api/market-data/candles/5m`. |

---

## Schema summary: `market_data_bars_5m`

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

1. **Script:** `python scripts/run_candles_5m_ingestion.py [--limit N]` (from `api/`).
2. **Ingestion:** Load instruments with `provider=binance`, `is_active=true`; for each, call `fetch_klines_5m(provider_symbol, limit)` (Binance REST `/api/v3/klines?interval=5m`); for each candle, `upsert_bar_5m(...)`; single `commit()` at the end.
3. **Client:** `fetch_klines_5m` returns normalized list of `{ open_time, open, high, low, close, volume }`.

---

## REST endpoint: GET /api/market-data/candles/5m

- **Query params:** `symbol` (e.g. BTCUSDT) or `instrument_id` (exactly one required). Optional: `start_time`, `end_time` (ISO 8601), `limit` (default 300, max 500).
- **Validation:** 400 if both `symbol` and `instrument_id` missing, or both provided. 400 if `start_time`/`end_time` invalid. Empty list if instrument not found or no bars.
- **Response:** `{ "candles": [ { "instrument_id", "symbol", "open_time", "open", "high", "low", "close", "volume" } ] }`.

---

## Intentionally not implemented

- Other timeframes (1m, 15m, 1h, 4h, 1d, 1w).
- Multi-timeframe abstraction.
- WebSocket kline streaming.
- Yahoo or other providers for 5m.
- Ingestion from FastAPI startup.
- Redis or schema changes to existing tables.

---

## Operational notes: running 5m candle ingestion

- **From api/:** `python scripts/run_candles_5m_ingestion.py` or `python scripts/run_candles_5m_ingestion.py --limit 300`.
- **When:** Run manually for backfill or on a schedule (e.g. cron every 5–15 minutes) to keep recent 5m bars updated. Not started from FastAPI.
- **Instruments:** Only instruments with `provider=binance` and `is_active=true` and non-empty `provider_symbol` are ingested.
- **Limit:** Up to 500 klines per symbol per run (Binance max 1000; default 500). Use `--limit` to reduce.
