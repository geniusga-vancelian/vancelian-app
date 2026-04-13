"""
Lance le backfill des barres en retard (5m, 1h, 4h, 1d, 1w) puis affiche
l'état en base (trous / retard) via compute_ohlc_holes_for_instruments.
Usage: depuis api/ : python scripts/run_backfill_lag_and_analyze.py
"""
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from database import SessionLocal, MarketDataInstrument
from services.market_data.candles_backfill_service import run_backfill
from services.market_data.ohlc_holes import compute_ohlc_holes_for_instruments

BACKFILL_TIMEFRAMES = ["5m", "1h", "4h", "1d", "1w"]


def main():
    db = SessionLocal()
    try:
        print("=== 1. Backfill des barres en retard (dernière barre → maintenant) ===\n")
        for tf in BACKFILL_TIMEFRAMES:
            summary = run_backfill(db, timeframe=tf, symbol=None)
            print(f"  [{tf}] instruments_processed={summary.get('instruments_processed', 0)} "
                  f"candles_fetched={summary.get('candles_fetched', 0)} "
                  f"candles_upserted={summary.get('candles_upserted', 0)} "
                  f"commits={summary.get('commits_performed', 0)}")
            errs = summary.get("errors") or []
            if errs:
                for e in errs[:5]:
                    print(f"       ERROR: {e}")
                if len(errs) > 5:
                    print(f"       ... et {len(errs) - 5} autre(s) erreur(s)")

        print("\n=== 2. Instruments crypto Binance (IDs pour analyse) ===\n")
        rows = (
            db.query(MarketDataInstrument.id, MarketDataInstrument.provider_symbol, MarketDataInstrument.symbol)
            .filter(
                MarketDataInstrument.asset_class == "crypto",
                MarketDataInstrument.provider == "binance",
            )
            .order_by(MarketDataInstrument.symbol)
            .all()
        )
        if not rows:
            print("  Aucun instrument crypto Binance trouvé.")
            return
        ids = [r[0] for r in rows]
        for r in rows:
            print(f"  id={r[0]} symbol={r[2]} provider_symbol={r[1]}")
        print(f"  Total: {len(ids)} instruments\n")

        print("=== 3. Analyse trous / retard après backfill ===\n")
        data = compute_ohlc_holes_for_instruments(db, ids)
        for row in data[:5]:  # premier instrument détaillé
            print(f"  Instrument {row['instrument_id']} ({row['symbol']}):")
            for period in ("M5", "H1", "H4", "D1", "W1"):
                info = row.get(period) or {}
                bar_count = info.get("bar_count") or 0
                expected = info.get("expected_bar_count") or 0
                missing_to_now = info.get("missing_bars_to_now")
                lag = info.get("lag_note") or "—"
                holes_count = len(info.get("holes") or [])
                print(f"    {period}: bar_count={bar_count} expected={expected} missing_to_now={missing_to_now} "
                      f"lag_note={lag!r} holes={holes_count}")
            print()
        if len(data) > 5:
            print(f"  ... et {len(data) - 5} autre(s) instrument(s). Résumé global:")
        total_missing = 0
        for row in data:
            for period in ("M5", "H1", "H4", "D1", "W1"):
                m = row.get(period) or {}
                n = m.get("missing_bars_to_now")
                if n is not None and n > 0:
                    total_missing += n
        print(f"  Total barres manquantes (retard) tous instruments/timeframes: {total_missing}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
