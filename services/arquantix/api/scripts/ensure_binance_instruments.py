#!/usr/bin/env python3
"""
Créer en base les instruments Binance nécessaires pour market-summary, top-movers et WebSocket.
À lancer une fois (ou après reset DB). Puis lancer l'ingestion des quotes (REST ou WS).

Usage (depuis la racine du repo ou depuis api/):
  python -m scripts.ensure_binance_instruments
  cd api && python -m scripts.ensure_binance_instruments
"""
import sys
from pathlib import Path

# Allow running as script from api/ or repo root
api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401 — force mapper init
from database import SessionLocal, MarketDataInstrument

# Paires utilisées par le Flutter (defaultPopularSymbols) + quelques autres pour top-movers
BINANCE_CRYPTO_SYMBOLS = [
    ("BTCUSDT", "Bitcoin"),
    ("ETHUSDT", "Ethereum"),
    ("SOLUSDT", "Solana"),
    ("XRPUSDT", "XRP"),
    ("BNBUSDT", "BNB"),
    ("ADAUSDT", "Cardano"),
    ("DOGEUSDT", "Dogecoin"),
    ("USDCUSDT", "USD Coin"),
    ("AVAXUSDT", "Avalanche"),
    ("LINKUSDT", "Chainlink"),
    ("DOTUSDT", "Polkadot"),
]

BINANCE_FX_SYMBOLS = [
    ("EURUSDT", "EUR/USDT"),
]


def _ensure_instruments(db, symbols, asset_class):
    """Create or update instruments for the given (provider_symbol, name) list."""
    created = 0
    for provider_symbol, name in symbols:
        existing = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == provider_symbol)
            .first()
        )
        if existing:
            if existing.provider != "binance" or existing.is_active != "true":
                existing.provider = "binance"
                existing.is_active = "true"
                if existing.name != name:
                    existing.name = name
                db.commit()
                print(f"  → Updated: {provider_symbol} ({name})")
            continue
        new_inst = MarketDataInstrument(
            symbol=provider_symbol,
            name=name,
            asset_class=asset_class,
            weekend_tradable="true",
            provider="binance",
            provider_symbol=provider_symbol,
            is_active="true",
        )
        db.add(new_inst)
        db.commit()
        db.refresh(new_inst)
        created += 1
        print(f"  → Created: {provider_symbol} ({name}) [{asset_class}]")
    return created


def ensure_binance_instruments():
    db = SessionLocal()
    try:
        c1 = _ensure_instruments(db, BINANCE_CRYPTO_SYMBOLS, "crypto")
        c2 = _ensure_instruments(db, BINANCE_FX_SYMBOLS, "forex")
        total = c1 + c2
        if total == 0:
            print("  → All Binance instruments already present.")
        else:
            print(f"  → {total} instrument(s) created.")
    finally:
        db.close()


if __name__ == "__main__":
    print("Ensuring Binance instruments for market-data / Flutter Markets...")
    ensure_binance_instruments()
    print("Done.")
