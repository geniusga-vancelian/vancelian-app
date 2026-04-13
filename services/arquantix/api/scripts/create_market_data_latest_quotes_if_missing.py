#!/usr/bin/env python3
"""
Crée la table market_data_latest_quotes si elle n'existe pas.
Utile quand les migrations Alembic sont en état incohérent.

Usage: cd api && python3 scripts/create_market_data_latest_quotes_if_missing.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from database import engine


SQL_LATEST_QUOTES = """
CREATE TABLE IF NOT EXISTS public.market_data_latest_quotes (
    instrument_id INTEGER NOT NULL REFERENCES public.market_data_instruments(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_symbol VARCHAR(50),
    last_price NUMERIC(20, 8) NOT NULL,
    bid_price NUMERIC(20, 8),
    ask_price NUMERIC(20, 8),
    volume NUMERIC(20, 8),
    quote_time TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_id)
);
CREATE INDEX IF NOT EXISTS ix_market_data_latest_quotes_instrument_id
    ON public.market_data_latest_quotes (instrument_id);
"""

SQL_BARS_5M = """
CREATE TABLE IF NOT EXISTS public.market_data_bars_5m (
    instrument_id INTEGER NOT NULL REFERENCES public.market_data_instruments(id) ON DELETE CASCADE,
    open_time TIMESTAMP WITH TIME ZONE NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(20, 8) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'binance',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_id, open_time)
);
CREATE INDEX IF NOT EXISTS ix_market_data_bars_5m_instrument_id ON public.market_data_bars_5m (instrument_id);
CREATE INDEX IF NOT EXISTS ix_market_data_bars_5m_open_time ON public.market_data_bars_5m (open_time);
"""

SQL_BARS_1H = """
CREATE TABLE IF NOT EXISTS public.market_data_bars_1h (
    instrument_id INTEGER NOT NULL REFERENCES public.market_data_instruments(id) ON DELETE CASCADE,
    open_time TIMESTAMP WITH TIME ZONE NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(20, 8) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'binance',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_id, open_time)
);
CREATE INDEX IF NOT EXISTS ix_market_data_bars_1h_instrument_id ON public.market_data_bars_1h (instrument_id);
CREATE INDEX IF NOT EXISTS ix_market_data_bars_1h_open_time ON public.market_data_bars_1h (open_time);
"""


def main():
    with engine.connect() as conn:
        for stmt in SQL_LATEST_QUOTES.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        for stmt in SQL_BARS_5M.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        for stmt in SQL_BARS_1H.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    print("Tables market_data_latest_quotes, market_data_bars_5m et market_data_bars_1h OK.")


if __name__ == "__main__":
    main()
