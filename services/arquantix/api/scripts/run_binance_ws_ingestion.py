"""
Run Binance Spot WebSocket ingestion for latest quotes (bookTicker stream).
Usage: python scripts/run_binance_ws_ingestion.py

Runs until interrupted (SIGINT/SIGTERM). Uses combined stream, batch commits, reconnect with backoff.
Expects to be run from the api/ directory (or with api/ on PYTHONPATH).

Note: This worker supersedes the REST polling script (run_binance_ingestion.py) for latest quotes
when running in production. The polling script remains available as a fallback.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401 — force mapper init for Person ↔ Client relationship
from services.market_data.binance_ws_ingestion import run_ws_ingestion


def main() -> int:
    run_ws_ingestion()
    return 0


if __name__ == "__main__":
    sys.exit(main())
