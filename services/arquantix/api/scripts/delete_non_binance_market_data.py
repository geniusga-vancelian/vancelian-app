#!/usr/bin/env python3
"""
Delete all market data that is NOT from Binance (Yahoo and other providers).
Keeps only instruments with provider='binance' and their related data.

Steps:
1. List instrument IDs where provider != 'binance'
2. Delete or null FK references: backtest_instrument_series, backtest_metrics (null),
   bundle_components (null), latest_quotes, bars_d1, bars_5m, bars_1h, bars_4h, bars_1d, bars_1w
3. Delete market_data_instruments where provider != 'binance'

Usage:
  python scripts/delete_non_binance_market_data.py --dry-run   # show what would be deleted
  python scripts/delete_non_binance_market_data.py --confirm   # perform deletion

Expects to be run from the api/ directory (or with api/ on PYTHONPATH).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    SessionLocal,
    MarketDataInstrument,
    MarketDataLatestQuote,
    MarketDataBarD1,
    MarketDataBar5m,
    MarketDataBar1h,
    MarketDataBar4h,
    MarketDataBar1d,
    MarketDataBar1w,
)
from database import BundleComponent, BacktestInstrumentSeries, BacktestMetrics


def get_non_binance_instrument_ids(session):
    """Return list of instrument IDs where provider != 'binance'."""
    rows = (
        session.query(MarketDataInstrument.id, MarketDataInstrument.symbol, MarketDataInstrument.provider)
        .filter(MarketDataInstrument.provider != "binance")
        .all()
    )
    return [(r.id, r.symbol, r.provider) for r in rows]


def run(dry_run: bool, confirm: bool) -> int:
    if not dry_run and not confirm:
        print("Use --dry-run to see what would be deleted, or --confirm to perform deletion.")
        return 1

    db = SessionLocal()
    try:
        non_binance = get_non_binance_instrument_ids(db)
        if not non_binance:
            print("No non-Binance instruments found. Nothing to delete.")
            return 0

        ids = [x[0] for x in non_binance]
        print(f"Found {len(non_binance)} non-Binance instrument(s):")
        for _id, symbol, provider in non_binance[:30]:
            print(f"  id={_id} symbol={symbol} provider={provider}")
        if len(non_binance) > 30:
            print(f"  ... and {len(non_binance) - 30} more")

        if dry_run:
            # Count rows that would be affected
            n_quotes = db.query(MarketDataLatestQuote).filter(MarketDataLatestQuote.instrument_id.in_(ids)).count()
            n_d1 = db.query(MarketDataBarD1).filter(MarketDataBarD1.instrument_id.in_(ids)).count()
            n_5m = db.query(MarketDataBar5m).filter(MarketDataBar5m.instrument_id.in_(ids)).count()
            n_1h = db.query(MarketDataBar1h).filter(MarketDataBar1h.instrument_id.in_(ids)).count()
            n_4h = db.query(MarketDataBar4h).filter(MarketDataBar4h.instrument_id.in_(ids)).count()
            n_1d = db.query(MarketDataBar1d).filter(MarketDataBar1d.instrument_id.in_(ids)).count()
            n_1w = db.query(MarketDataBar1w).filter(MarketDataBar1w.instrument_id.in_(ids)).count()
            n_bundle = db.query(BundleComponent).filter(BundleComponent.instrument_id.in_(ids)).count()
            n_bt_series = db.query(BacktestInstrumentSeries).filter(BacktestInstrumentSeries.instrument_id.in_(ids)).count()
            n_bt_metrics = db.query(BacktestMetrics).filter(BacktestMetrics.instrument_id.in_(ids)).count()

            print("\n[DRY-RUN] Would delete/null:")
            print(f"  market_data_latest_quotes: {n_quotes} rows")
            print(f"  market_data_bars_d1:      {n_d1} rows")
            print(f"  market_data_bars_5m:      {n_5m} rows")
            print(f"  market_data_bars_1h:      {n_1h} rows")
            print(f"  market_data_bars_4h:      {n_4h} rows")
            print(f"  market_data_bars_1d:      {n_1d} rows")
            print(f"  market_data_bars_1w:      {n_1w} rows")
            print(f"  bundle_components:        {n_bundle} rows (instrument_id set to NULL)")
            print(f"  backtest_instrument_series: {n_bt_series} rows")
            print(f"  backtest_metrics:         {n_bt_metrics} rows (instrument_id set to NULL)")
            print(f"  market_data_instruments: {len(ids)} rows")
            return 0

        # Perform deletion
        print("\nDeleting dependent data and non-Binance instruments...")

        db.query(MarketDataLatestQuote).filter(MarketDataLatestQuote.instrument_id.in_(ids)).delete(synchronize_session=False)
        db.query(MarketDataBarD1).filter(MarketDataBarD1.instrument_id.in_(ids)).delete(synchronize_session=False)
        db.query(MarketDataBar5m).filter(MarketDataBar5m.instrument_id.in_(ids)).delete(synchronize_session=False)
        db.query(MarketDataBar1h).filter(MarketDataBar1h.instrument_id.in_(ids)).delete(synchronize_session=False)
        db.query(MarketDataBar4h).filter(MarketDataBar4h.instrument_id.in_(ids)).delete(synchronize_session=False)
        db.query(MarketDataBar1d).filter(MarketDataBar1d.instrument_id.in_(ids)).delete(synchronize_session=False)
        db.query(MarketDataBar1w).filter(MarketDataBar1w.instrument_id.in_(ids)).delete(synchronize_session=False)

        db.query(BacktestInstrumentSeries).filter(BacktestInstrumentSeries.instrument_id.in_(ids)).delete(synchronize_session=False)
        db.query(BundleComponent).filter(BundleComponent.instrument_id.in_(ids)).update(
            {BundleComponent.instrument_id: None}, synchronize_session=False
        )
        db.query(BacktestMetrics).filter(BacktestMetrics.instrument_id.in_(ids)).update(
            {BacktestMetrics.instrument_id: None}, synchronize_session=False
        )

        db.query(MarketDataInstrument).filter(MarketDataInstrument.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        print(f"Done. Removed {len(ids)} non-Binance instruments and their market data.")
        return 0
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Delete market data for non-Binance instruments (Yahoo, etc.). Keep only Binance.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without writing")
    parser.add_argument("--confirm", action="store_true", help="Confirm and perform deletion")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, confirm=args.confirm)


if __name__ == "__main__":
    sys.exit(main())
