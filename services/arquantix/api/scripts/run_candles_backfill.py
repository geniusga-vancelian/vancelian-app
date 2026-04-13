"""
Incremental candle backfill: download only missing candlesticks from latest DB candle to now.
Usage:
  python scripts/run_candles_backfill.py --timeframe 5m
  python scripts/run_candles_backfill.py --timeframe 1h --symbol BTCUSDT
  python scripts/run_candles_backfill.py --timeframe 1d --fallback-days 3650
  python scripts/run_candles_backfill.py --timeframe 1w --dry-run

Expects to be run from the api/ directory (or with api/ on PYTHONPATH).
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from services.market_data.candles_backfill_service import (
    SUPPORTED_TIMEFRAMES,
    TIMEFRAME_CONFIG,
    DEFAULT_LIMIT_PER_REQUEST,
    DEFAULT_COMMIT_BATCH,
    run_backfill,
)


def _default_fallback_days(timeframe: str) -> int:
    return TIMEFRAME_CONFIG[timeframe]["fallback_days"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Incremental backfill: fetch missing candles from latest DB candle to now",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        required=True,
        choices=SUPPORTED_TIMEFRAMES,
        help="Candle timeframe to backfill (5m, 1h, 4h, 1d, 1w)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Backfill only this provider symbol (e.g. BTCUSDT). If omitted, all active Binance instruments.",
    )
    parser.add_argument(
        "--limit-per-request",
        type=int,
        default=DEFAULT_LIMIT_PER_REQUEST,
        help=f"Binance klines limit per request (default {DEFAULT_LIMIT_PER_REQUEST})",
    )
    parser.add_argument(
        "--fallback-days",
        type=int,
        default=None,
        help="Days to look back when no candle exists in DB (default: 5m=7, 1h=30, 4h=120, 1d=730, 1w=3650)",
    )
    parser.add_argument(
        "--commit-batch",
        type=int,
        default=DEFAULT_COMMIT_BATCH,
        help=f"Commit after this many fetch batches (default {DEFAULT_COMMIT_BATCH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and log what would be fetched; do not write to DB",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger(__name__)

    limit = max(1, min(args.limit_per_request, 1000))
    commit_batch = max(1, args.commit_batch)
    fallback = args.fallback_days
    if fallback is not None and fallback < 1:
        logger.warning("fallback-days < 1, using default for timeframe")
        fallback = _default_fallback_days(args.timeframe)

    db = SessionLocal()
    try:
        summary = run_backfill(
            db,
            timeframe=args.timeframe,
            symbol=args.symbol,
            limit_per_request=limit,
            fallback_days=fallback,
            commit_batch=commit_batch,
            dry_run=args.dry_run,
        )
        print("Candle backfill summary:")
        print(f"  Timeframe: {args.timeframe}")
        print(f"  Instruments processed: {summary['instruments_processed']}")
        print(f"  Candles fetched: {summary['candles_fetched']}")
        print(f"  Candles upserted: {summary['candles_upserted']}")
        print(f"  Commits performed: {summary['commits_performed']}")
        if summary["errors"]:
            print("  Errors:")
            for msg in summary["errors"]:
                print(f"    - {msg}")
        if summary["skipped"]:
            print("  Skipped:")
            for s in summary["skipped"]:
                print(f"    - {s}")
        if args.dry_run:
            print("  (dry-run: no data written)")
        if summary["errors"] and summary["candles_upserted"] == 0 and not args.dry_run:
            return 1
        return 0
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
