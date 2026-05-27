#!/usr/bin/env python3
"""
Seed bridge: market_data_instruments → pe_assets + pe_instruments (spot).

Creates or updates pe_assets and pe_instruments for Base-allowed cryptos
(``config.base_allowed_assets``) present in market_data_instruments.

Idempotent: safe to run multiple times.  Existing records are matched by
pe_assets.symbol (e.g. "BTC") and pe_instruments.code (e.g. "BTC-SPOT").
Metadata is merged, never overwritten destructively.

Usage (from api/ or repo root):
    python -m scripts.seed_pe_crypto_assets
    cd api && python3 scripts/seed_pe_crypto_assets.py
"""
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from config.base_allowed_assets import BASE_ALLOWED_ASSETS
from database import SessionLocal, MarketDataInstrument
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument

# ────────────────────────────────────────────────────────────────────────────
# provider_symbol → seed parameters (Base allowed only, one row per pair)
# ────────────────────────────────────────────────────────────────────────────

_KIND_SEED = {
    "native": {
        "asset_type": "crypto",
        "risk_profile": "moderate",
        "supports_staking": True,
        "supports_collateral": True,
    },
    "stablecoin": {
        "asset_type": "stablecoin",
        "risk_profile": "conservative",
        "supports_staking": False,
        "supports_collateral": True,
    },
    "wrapped_btc": {
        "asset_type": "crypto",
        "risk_profile": "moderate",
        "supports_staking": False,
        "supports_collateral": True,
    },
    "wrapped_eth": {
        "asset_type": "crypto",
        "risk_profile": "moderate",
        "supports_staking": False,
        "supports_collateral": True,
    },
    "token": {
        "asset_type": "crypto",
        "risk_profile": "aggressive",
        "supports_staking": False,
        "supports_collateral": False,
    },
}


def _build_crypto_bridge_entries() -> list[dict]:
    entries: list[dict] = []
    for row in BASE_ALLOWED_ASSETS:
        kind = row.get("kind", "token")
        seed = _KIND_SEED.get(kind, _KIND_SEED["token"])
        entries.append(
            {
                "asset_symbol": row["symbol"],
                "asset_name": row["name"],
                "provider_symbol": row["provider_symbol"],
                **seed,
            }
        )
    return entries


CRYPTO_BRIDGE_ENTRIES = _build_crypto_bridge_entries()

BRIDGE_METADATA_KEYS = frozenset({
    "market_data_instrument_id",
    "provider_symbol",
    "legacy_symbol",
    "seed_source",
    "market_data_symbol",
})


def _merge_bridge_metadata(existing, bridge_fields: dict) -> dict:
    """Merge bridge-specific keys into existing metadata without destroying other keys."""
    merged = dict(existing or {})
    merged.update(bridge_fields)
    return merged


def seed_pe_crypto_assets() -> None:
    db = SessionLocal()
    try:
        # ── Step 1: load source instruments from market_data_instruments ──
        provider_symbols = list({e["provider_symbol"] for e in CRYPTO_BRIDGE_ENTRIES})
        source_rows = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol.in_(provider_symbols))
            .all()
        )
        source_by_ps = {
            row.provider_symbol: row for row in source_rows
        }

        missing = [ps for ps in provider_symbols if ps not in source_by_ps]
        if missing:
            print(f"  ⚠ Skipping missing market_data_instruments: {missing}")

        if not source_by_ps:
            print("  ✗ FATAL: no market_data_instruments matched the bridge map.")
            print("    Run sync_base_allowed_instruments.py or ensure_binance_instruments.py first.")
            sys.exit(1)

        print(f"  ✓ Bridging {len(source_by_ps)} instrument(s) from market_data_instruments")

        assets_created = 0
        assets_updated = 0
        assets_skipped = 0
        instruments_created = 0
        instruments_updated = 0
        instruments_skipped = 0

        for cfg in CRYPTO_BRIDGE_ENTRIES:
            provider_symbol = cfg["provider_symbol"]
            md_inst = source_by_ps.get(provider_symbol)
            if md_inst is None:
                continue
            ticker = cfg["asset_symbol"]

            # ── Asset bridge metadata ────────────────────────────────
            asset_bridge_meta = {
                "market_data_instrument_id": md_inst.id,
                "provider_symbol": provider_symbol,
                "legacy_symbol": md_inst.symbol,
                "seed_source": "market_data_bridge_v1",
            }

            # ── pe_asset ─────────────────────────────────────────────
            pe_asset = (
                db.query(Asset)
                .filter(Asset.symbol == ticker)
                .first()
            )

            if pe_asset is None:
                pe_asset = Asset(
                    symbol=ticker,
                    name=cfg["asset_name"],
                    asset_type=cfg["asset_type"],
                    valuation_source="binance",
                    liquidity_profile="high",
                    risk_profile=cfg["risk_profile"],
                    supports_staking=cfg["supports_staking"],
                    supports_collateral=cfg["supports_collateral"],
                    supports_borrowing=False,
                    supports_yield=False,
                    metadata_=asset_bridge_meta,
                )
                db.add(pe_asset)
                db.flush()
                assets_created += 1
                print(f"  + pe_asset CREATED: {ticker} (id={pe_asset.id})")
            else:
                current_meta = pe_asset.metadata_ or {}
                needs_update = any(
                    current_meta.get(k) != asset_bridge_meta[k]
                    for k in asset_bridge_meta
                )
                if needs_update:
                    pe_asset.metadata_ = _merge_bridge_metadata(current_meta, asset_bridge_meta)
                    db.flush()
                    assets_updated += 1
                    print(f"  ~ pe_asset UPDATED metadata: {ticker}")
                else:
                    assets_skipped += 1
                    print(f"  = pe_asset OK (skipped): {ticker}")

            # ── Instrument bridge metadata ───────────────────────────
            inst_code = f"{ticker}-SPOT"
            inst_bridge_meta = {
                "market_data_instrument_id": md_inst.id,
                "provider_symbol": provider_symbol,
                "legacy_symbol": md_inst.symbol,
                "market_data_symbol": md_inst.symbol,
                "seed_source": "market_data_bridge_v1",
            }

            # ── pe_instrument ────────────────────────────────────────
            pe_inst = (
                db.query(Instrument)
                .filter(Instrument.code == inst_code)
                .first()
            )

            if pe_inst is None:
                pe_inst = Instrument(
                    asset_id=pe_asset.id,
                    code=inst_code,
                    name=f"{cfg['asset_name']} Spot",
                    instrument_type="spot",
                    liquidity_profile="high",
                    lockup_period_days=None,
                    valuation_method="market_quote",
                    yield_source=None,
                    provider="binance",
                    metadata_=inst_bridge_meta,
                )
                db.add(pe_inst)
                db.flush()
                instruments_created += 1
                print(f"  + pe_instrument CREATED: {inst_code} (id={pe_inst.id})")
            else:
                current_meta = pe_inst.metadata_ or {}
                needs_update = any(
                    current_meta.get(k) != inst_bridge_meta[k]
                    for k in inst_bridge_meta
                )
                if needs_update:
                    pe_inst.metadata_ = _merge_bridge_metadata(current_meta, inst_bridge_meta)
                    db.flush()
                    instruments_updated += 1
                    print(f"  ~ pe_instrument UPDATED metadata: {inst_code}")
                else:
                    instruments_skipped += 1
                    print(f"  = pe_instrument OK (skipped): {inst_code}")

        db.commit()

        print()
        print("  ── Summary ──────────────────────────────────────────")
        print(f"  pe_assets    : {assets_created} created, {assets_updated} updated, {assets_skipped} skipped")
        print(f"  pe_instruments: {instruments_created} created, {instruments_updated} updated, {instruments_skipped} skipped")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding Portfolio Engine from market_data_instruments (crypto bridge v1)...")
    print()
    seed_pe_crypto_assets()
    print()
    print("Done.")
