# Market Data Step 1 – Implemented

**Date:** 2026-02-18  
**Scope:** Database foundation for latest crypto quotes only (snapshot table, model, repository). No Binance ingestion, no WebSocket, no REST endpoints, no OHLC/intraday.

---

## Files created

| File | Description |
|------|-------------|
| `api/alembic/versions/015_add_market_data_latest_quotes.py` | Alembic migration: creates table `market_data_latest_quotes`. |
| `api/services/market_data/quotes_repo.py` | Repository: `get_latest_quotes_by_instrument_ids`, `get_latest_quotes_by_symbols`, `upsert_latest_quote`. |
| `docs/audit/MARKET_DATA_STEP1_IMPLEMENTED.md` | This note. |

---

## Files modified

| File | Change |
|------|--------|
| `api/database.py` | Added SQLAlchemy model `MarketDataLatestQuote` and relationship to `MarketDataInstrument`. |

---

## Migration

- **Revision ID:** `015`
- **Down revision:** `014`
- **Name:** `add_market_data_latest_quotes`

---

## Table schema: `market_data_latest_quotes`

| Column | Type | Nullable | Notes |
|--------|------|----------|--------|
| `instrument_id` | integer | NOT NULL | PK, FK → `market_data_instruments.id` (ON DELETE CASCADE) |
| `provider` | varchar(50) | NOT NULL | e.g. "binance", "yahoo" |
| `provider_symbol` | varchar(50) | YES | e.g. "BTCUSDT" |
| `last_price` | numeric(20,8) | NOT NULL | |
| `bid_price` | numeric(20,8) | YES | |
| `ask_price` | numeric(20,8) | YES | |
| `volume` | numeric(20,8) | YES | |
| `quote_time` | timestamptz | YES | Quote time from provider |
| `updated_at` | timestamptz | NOT NULL | Server default `now()`, updated on row change |

- **Constraint:** One row per instrument (`instrument_id` is the primary key).
- **Index:** `ix_market_data_latest_quotes_instrument_id` on `instrument_id`.

---

## Repository functions

- **`get_latest_quotes_by_instrument_ids(session, instrument_ids)`**  
  Returns list of `MarketDataLatestQuote` for the given instrument IDs. Empty list if `instrument_ids` is empty.

- **`get_latest_quotes_by_symbols(session, symbols)`**  
  Returns list of `MarketDataLatestQuote` for instruments whose **internal** `symbol` is in `symbols` (join with `market_data_instruments`). Empty list if `symbols` is empty.

- **`upsert_latest_quote(session, *, instrument_id, provider, provider_symbol, last_price, bid_price=None, ask_price=None, volume=None, quote_time=None)`**  
  Inserts a new row or updates the existing row for `instrument_id`. Returns the created or updated `MarketDataLatestQuote`. **Caller must commit the session** (no commit inside the repo).

---

## Assumptions

- Session lifecycle and commit are the caller’s responsibility (same as `bars_d1_repo`).
- `symbols` in `get_latest_quotes_by_symbols` refer to `MarketDataInstrument.symbol` (internal symbol), not `provider_symbol`.
- Numeric fields are passed as Python `float`; SQLAlchemy maps them to `Numeric(20,8)`.
- `quote_time` is passed as a timezone-aware datetime or None; stored as-is.
- No change to existing market_data routes, Yahoo ingestion, or D1 bars.

---

## What was intentionally NOT implemented

- Binance client or ingestion.
- WebSocket or REST endpoints for quotes.
- OHLC / klines / intraday bars or new bar tables.
- Any refactor of unrelated modules.
