#!/usr/bin/env python3
"""
Créer en base les instruments Binance nécessaires pour market-summary, top-movers et WebSocket.
Limite au périmètre ``config.base_allowed_assets`` (+ EURUSDT pour cotation EURC).

Préférer ``sync_base_allowed_instruments`` pour activer/désactiver le catalogue complet.

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
from config.base_allowed_assets import BASE_ALLOWED_ASSETS
from database import SessionLocal, MarketDataInstrument

BINANCE_FX_SYMBOLS = [
    ("EURUSDT", "EUR/USDT"),
]


def _base_crypto_symbols():
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for row in BASE_ALLOWED_ASSETS:
        ps = row["provider_symbol"]
        if ps in seen:
            continue
        seen.add(ps)
        out.append((ps, row["name"]))
    return out


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
        c1 = _ensure_instruments(db, _base_crypto_symbols(), "crypto")
        c2 = _ensure_instruments(db, BINANCE_FX_SYMBOLS, "forex")
        total = c1 + c2
        if total == 0:
            print("  → All Binance instruments already present.")
        else:
            print(f"  → {total} instrument(s) created.")
        print("  → Run sync_base_allowed_instruments to deactivate out-of-scope cryptos.")
    finally:
        db.close()


if __name__ == "__main__":
    print("Ensuring Binance instruments (Base allowed + EURUSDT)...")
    ensure_binance_instruments()
