"""
Run one Binance 1d candle ingestion cycle (backfill / poll recent klines).
Usage: python scripts/run_candles_1d_ingestion.py [--limit N]

Expects to be run from the api/ directory (or with api/ on PYTHONPATH).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from services.market_data.ingestion_binance_candles_1d import run_one_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Binance 1d candles into market_data_bars_1d")
    parser.add_argument("--limit", type=int, default=500, help="Max klines per symbol (default 500)")
    args = parser.parse_args()
    limit = max(1, min(args.limit, 1000))

    db = SessionLocal()
    try:
        upserted, failure_count, errors = run_one_cycle(db, limit_per_symbol=limit)
        print("Binance 1d candle ingestion:")
        print(f"  Candles upserted: {upserted}")
        print(f"  Symbol failures: {failure_count}")
        if errors:
            for msg in errors:
                print(f"    - {msg}")
        if failure_count > 0 and upserted == 0:
            return 1
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
