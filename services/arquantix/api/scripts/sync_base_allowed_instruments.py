#!/usr/bin/env python3
"""
Synchronise ``market_data_instruments`` avec ``config.base_allowed_assets``.

- Active / crée les instruments Binance autorisés (cotation)
- Désactive les autres cryptos actifs (hors périmètre Base produit)

Usage:
  cd services/arquantix/api && python -m scripts.sync_base_allowed_instruments
  python -m scripts.sync_base_allowed_instruments --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401

from config.base_allowed_assets import BASE_ALLOWED_ASSETS
from database import MarketDataInstrument, SessionLocal


def sync_base_allowed_instruments(*, dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        allowed_provider_symbols = {a["provider_symbol"] for a in BASE_ALLOWED_ASSETS}
        created = 0
        updated = 0

        for row in BASE_ALLOWED_ASSETS:
            provider_symbol = row["provider_symbol"]
            name = row["name"]
            existing = (
                db.query(MarketDataInstrument)
                .filter(MarketDataInstrument.provider_symbol == provider_symbol)
                .first()
            )
            if existing:
                changed = False
                if existing.name != name:
                    existing.name = name
                    changed = True
                if existing.provider != "binance":
                    existing.provider = "binance"
                    changed = True
                if existing.asset_class != "crypto":
                    existing.asset_class = "crypto"
                    changed = True
                if existing.is_active != "true":
                    existing.is_active = "true"
                    changed = True
                if existing.symbol != provider_symbol:
                    existing.symbol = provider_symbol
                    changed = True
                if changed:
                    updated += 1
                    print(f"  → Update: {provider_symbol} ({name})")
                    if not dry_run:
                        db.commit()
                continue

            print(f"  → Create: {provider_symbol} ({name})")
            if dry_run:
                created += 1
                continue
            db.add(
                MarketDataInstrument(
                    symbol=provider_symbol,
                    name=name,
                    asset_class="crypto",
                    weekend_tradable="true",
                    provider="binance",
                    provider_symbol=provider_symbol,
                    is_active="true",
                )
            )
            db.commit()
            created += 1

        deactivated = 0
        active_cryptos = (
            db.query(MarketDataInstrument)
            .filter(
                MarketDataInstrument.asset_class == "crypto",
                MarketDataInstrument.is_active == "true",
            )
            .all()
        )
        for inst in active_cryptos:
            ps = (inst.provider_symbol or inst.symbol or "").strip().upper()
            if ps in allowed_provider_symbols:
                continue
            print(f"  → Deactivate: {ps} ({inst.name})")
            if not dry_run:
                inst.is_active = "false"
                db.commit()
            deactivated += 1

        print(
            f"Done. created={created} updated={updated} deactivated={deactivated}"
            + (" (dry-run)" if dry_run else "")
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print("Syncing Base allowed instruments (market_data_instruments)...")
    sync_base_allowed_instruments(dry_run=args.dry_run)
