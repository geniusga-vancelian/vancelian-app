# Market Data Step 10 – Candles 4h / 1d / 1w (Implemented)

**Date:** 2026-02-18  
**Scope:** Additive implementation of historical candle timeframes 4h, 1d, 1w for Binance crypto instruments: persistent storage, repos, Binance client extension, ingestion modules/scripts, REST endpoints. No generic multi-timeframe abstraction; style aligned with existing 5m/1h.

---

## Files created

| File | Description |
|------|-------------|
| `api/alembic/versions/018_add_market_data_bars_4h.py` | Migration: table `market_data_bars_4h` (instrument_id, open_time, open, high, low, close, volume, source, updated_at; PK (instrument_id, open_time)). |
| `api/alembic/versions/019_add_market_data_bars_1d.py` | Migration: table `market_data_bars_1d` (same schema). |
| `api/alembic/versions/020_add_market_data_bars_1w.py` | Migration: table `market_data_bars_1w` (same schema). |
| `api/services/market_data/bars_4h_repo.py` | `get_bars_4h`, `upsert_bar_4h` (no commit inside repo). |
| `api/services/market_data/bars_1d_repo.py` | `get_bars_1d`, `upsert_bar_1d`. |
| `api/services/market_data/bars_1w_repo.py` | `get_bars_1w`, `upsert_bar_1w`. |
| `api/services/market_data/ingestion_binance_candles_4h.py` | Load Binance instruments, fetch 4h klines, upsert into bars_4h, one commit per cycle. |
| `api/services/market_data/ingestion_binance_candles_1d.py` | Same for 1d. |
| `api/services/market_data/ingestion_binance_candles_1w.py` | Same for 1w. |
| `api/scripts/run_candles_4h_ingestion.py` | CLI: run 4h ingestion with optional `--limit` (default 500, max 1000). |
| `api/scripts/run_candles_1d_ingestion.py` | CLI: run 1d ingestion. |
| `api/scripts/run_candles_1w_ingestion.py` | CLI: run 1w ingestion. |
| `docs/audit/MARKET_DATA_STEP10_IMPLEMENTED.md` | This document. |

---

## Files modified

| File | Change |
|------|--------|
| `api/database.py` | Added models `MarketDataBar4h`, `MarketDataBar1d`, `MarketDataBar1w` with backrefs `bars_4h`, `bars_1d`, `bars_1w`. |
| `api/services/market_data/binance_client.py` | Added `fetch_klines_4h`, `fetch_klines_1d`, `fetch_klines_1w` (interval 4h / 1d / 1w, same normalized output as 5m/1h). |
| `api/services/market_data/routes.py` | Imports `get_bars_4h`, `get_bars_1d`, `get_bars_1w`; added GET `/api/market-data/candles/4h`, `/candles/1d`, `/candles/1w` (public, same contract as 5m/1h). |

---

## New tables

- **market_data_bars_4h** – 4-hour candles (Binance).
- **market_data_bars_1d** – 1-day candles (Binance).
- **market_data_bars_1w** – 1-week candles (Binance).

Each: `instrument_id`, `open_time`, `open`, `high`, `low`, `close`, `volume`, `source`, `updated_at`; PK `(instrument_id, open_time)`; indexes on `instrument_id` and `open_time`.

---

## New REST endpoints (public, no auth)

| Method | Path | Query params | Response |
|--------|------|--------------|----------|
| GET | `/api/market-data/candles/4h` | `symbol` or `instrument_id` (exactly one), optional `start_time`, `end_time`, `limit` (default 300, max 500) | `{"candles": [{ instrument_id, symbol, open_time, open, high, low, close, volume }, ...]}` |
| GET | `/api/market-data/candles/1d` | Same | Same |
| GET | `/api/market-data/candles/1w` | Same | Same |

- 400 if both `symbol` and `instrument_id` missing or both provided; 400 on invalid datetime (ISO 8601); empty `candles` if no data or instrument not found.

---

## Backfill / cron usage

- **4h:** Use for “1M” view; recommend at least a few months of history. Example: `python scripts/run_candles_4h_ingestion.py --limit 500` (one run ≈ 500 candles per symbol; repeat or increase limit for more history).
- **1d:** Use for “1Y” view; recommend 1 year or more. Example: `python scripts/run_candles_1d_ingestion.py --limit 500` (Binance max 1000 per request; script caps at 1000; multiple runs or higher limit for full backfill).
- **1w:** Use for long-term / max view. Example: `python scripts/run_candles_1w_ingestion.py --limit 500`.

All scripts expect to be run from `api/` (or with `api/` on PYTHONPATH). No ingestion on FastAPI startup; backfill is entirely script-driven.

---

## Known limitations

- Binance klines API limit per request: 1000; scripts cap `--limit` at 1000. For very long history, run scripts multiple times (e.g. with `start_time`/`end_time` in a future enhancement) or accept gradual backfill.
- Only Binance instruments (provider=binance, is_active=true) are ingested; Yahoo and other providers unchanged.
- No Redis, no WebSocket candle ingestion, no generic multi-timeframe layer; implementation remains explicit per timeframe (4h, 1d, 1w) in line with 5m/1h.

---

## Intentionally not done in this step

- Generic multi-timeframe abstraction.
- Changes to latest quote schema, WebSocket quote ingestion, or Yahoo logic.
- Redis or FastAPI startup ingestion.
- WebSocket candle ingestion.
