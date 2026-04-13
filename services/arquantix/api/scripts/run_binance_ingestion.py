"""
Run one Binance latest-quote ingestion cycle.
Usage: python scripts/run_binance_ingestion.py

Expects to be run from the api/ directory (or with api/ on PYTHONPATH).
"""
import sys
from pathlib import Path

# Add parent directory so that "from database" and "from services.*" resolve
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force mapper init order (same as ensure_binance_instruments) — avoids Person/Client import errors.
from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401

from database import SessionLocal
from services.market_data.config import BINANCE_INGESTION_ENABLED
from services.market_data.ingestion_binance import run_one_cycle


def main() -> int:
    if not BINANCE_INGESTION_ENABLED:
        print("Binance ingestion is disabled (BINANCE_INGESTION_ENABLED=false). Exiting.")
        return 0

    db = SessionLocal()
    try:
        updated, failure_count, errors = run_one_cycle(db)
        total = updated + failure_count
        print("Binance latest-quote ingestion:")
        print(f"  Instruments (Binance, active): {total}")
        print(f"  Quotes updated: {updated}")
        print(f"  Failures: {failure_count}")
        if errors:
            for msg in errors:
                print(f"    - {msg}")
        if failure_count > 0 and updated == 0:
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
