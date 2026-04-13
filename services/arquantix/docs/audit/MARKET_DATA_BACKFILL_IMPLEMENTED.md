# Market Data – Incremental Candle Backfill (Implemented)

**Date:** 2026-02-18  
**Scope:** Dedicated incremental historical candle backfill: download only **missing** candlesticks between the latest candle in the DB and now. Supports 5m, 1h, 4h, 1d, 1w. Additive; does not replace existing ingestion scripts or change schema.

---

## Files created

| File | Description |
|------|-------------|
| `api/services/market_data/candles_backfill_service.py` | Backfill logic: timeframe mapping, load instruments, get latest DB candle, fetch Binance klines in batches, upsert via existing repos, commit in batches. |
| `api/scripts/run_candles_backfill.py` | CLI entrypoint: `--timeframe`, `--symbol`, `--limit-per-request`, `--fallback-days`, `--commit-batch`, `--dry-run`, `-v`. |
| `docs/audit/MARKET_DATA_BACKFILL_IMPLEMENTED.md` | This document. |

---

## Files modified

None. No schema changes; no changes to WebSocket, latest quote ingestion, or FastAPI startup.

---

## Supported timeframes

| Timeframe | Binance interval | Step | Default fallback days |
|-----------|-------------------|------|------------------------|
| 5m | 5m | 5 minutes | 7 |
| 1h | 1h | 1 hour | 30 |
| 4h | 4h | 4 hours | 120 |
| 1d | 1d | 1 day | 730 |
| 1w | 1w | 1 week | 3650 |

---

## How missing history is detected

1. **Per instrument and timeframe:** the service queries the relevant candle table for `max(open_time)` where `instrument_id = X`.
2. **If a latest candle exists:** backfill starts at `latest_open_time + step` (e.g. next 5m/1h/4h/1d/1w bar). No re-fetch of the same candle.
3. **If no candle exists:** backfill starts at `now - fallback_days`. Fallback days are configurable via `--fallback-days` or the defaults above.
4. **End:** backfill runs until the fetched candles reach “now” (no more data) or Binance returns no new candles.

---

## Pagination and safety

- **Batches:** Binance klines are requested with `start_time_ms`, optional `end_time_ms`, and `limit` (default 500, max 1000). After each batch, the next request uses `last_candle_open_time + step` as `start_time_ms`.
- **Loop guard:** if a batch does not advance the cursor (last `open_time` ≤ previous last), the loop stops to avoid infinite runs.
- **Empty response:** if Binance returns no candles for a request, backfill for that instrument stops.
- **Commits:** commits are performed every `--commit-batch` batches (default 5), plus a final commit for any remaining work. Repos do not commit; the service controls commits.

---

## CLI usage

From the `api/` directory:

```bash
# Backfill all active Binance instruments for 5m
python scripts/run_candles_backfill.py --timeframe 5m

# Backfill one symbol for 1h
python scripts/run_candles_backfill.py --timeframe 1h --symbol BTCUSDT

# 1d with 10 years of history when DB is empty
python scripts/run_candles_backfill.py --timeframe 1d --fallback-days 3650

# Dry-run: log what would be fetched, no DB writes
python scripts/run_candles_backfill.py --timeframe 1w --dry-run

# Tune batch size and commit frequency
python scripts/run_candles_backfill.py --timeframe 4h --limit-per-request 1000 --commit-batch 3 -v
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--timeframe` | Yes | One of: 5m, 1h, 4h, 1d, 1w |
| `--symbol` | No | Restrict to one provider symbol (e.g. BTCUSDT). If omitted, all active Binance instruments. |
| `--limit-per-request` | No | Binance klines per request (default 500, capped at 1000) |
| `--fallback-days` | No | When no candle exists in DB, look back this many days (defaults per timeframe above) |
| `--commit-batch` | No | Commit after this many fetch batches (default 5) |
| `--dry-run` | No | Only compute and log; do not write to DB |
| `-v` / `--verbose` | No | Enable INFO logging |

---

## Fallback when DB is empty

If there is **no** candle in the DB for the selected instrument/timeframe, the backfill start is set to `now - fallback_days`. Defaults:

- **5m:** 7 days  
- **1h:** 30 days  
- **4h:** 120 days  
- **1d:** 730 days (2 years)  
- **1w:** 3650 days (~10 years)

Override with `--fallback-days`. The script does **not** download full exchange history by default.

---

## Dry-run behavior

With `--dry-run`:

- Instruments are loaded and latest DB candle (if any) is computed.
- Start/end and batch requests are logged.
- Binance is called and candles are counted as “fetched”.
- **No** upserts and **no** commits. Summary shows “Candles upserted: 0” and “(dry-run: no data written)”.

---

## Instrument selection

- Only **Binance** instruments: `provider == "binance"`, `is_active == "true"`, `provider_symbol` non-empty.
- If `--symbol` is set: only that `provider_symbol` is backfilled. If it does not exist or is inactive, the script returns an error and exits with a non-zero code.

---

## Known limitations

- **One failure per instrument:** if backfill fails for one symbol (e.g. network or commit error), the service logs, rolls back uncommitted work for that symbol, and continues with the next. Already committed data for other symbols is kept.
- **Binance rate limits:** no built-in rate limiting; for large runs consider spacing or lowering `--limit-per-request`.
- **No schema change:** backfill uses existing candle tables and repos only.
- **Session scope:** one DB session for the whole run; commits are batched to limit transaction size.

---

## Intentionally not done

- No generic multi-timeframe engine; explicit mapping per timeframe.
- No WebSocket or latest-quote changes.
- No FastAPI startup integration.
- No Redis.
- No refactor of existing candle ingestion scripts; they remain the recommended way to “poll recent” candles; this script is for filling **historical** gaps.
