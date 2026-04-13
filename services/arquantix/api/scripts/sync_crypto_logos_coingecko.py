#!/usr/bin/env python3
"""
Sync crypto logos from CoinGecko for all crypto instruments in the database.

- Fetches coin list from CoinGecko, matches by symbol (and name if needed).
- Downloads logo image and saves to uploads/crypto_logos/{symbol}.png.
- Updates instrument.logo_filename in DB.

Usage (from api/ or repo root):
  python -m scripts.sync_crypto_logos_coingecko
  python -m scripts.sync_crypto_logos_coingecko --force   # re-download existing
  python -m scripts.sync_crypto_logos_coingecko --symbols BTC,ETH,SOL,XRP  # only these

Logos are stored in: api/uploads/crypto_logos/
Served at: /media/crypto_logos/{symbol}.png (MEDIA_BASE_URL + /media/...)
"""
import argparse
import sys
import time
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

import httpx
from database import SessionLocal, MarketDataInstrument

COINGECKO_LIST_URL = "https://api.coingecko.com/api/v3/coins/list"
COINGECKO_COIN_URL = "https://api.coingecko.com/api/v3/coins"
REQUEST_TIMEOUT = 30.0
DELAY_BETWEEN_COINS = 2.0  # avoid rate limit on free tier

# Prefer main CoinGecko coin when multiple coins share the same symbol
PREFERRED_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "xrp",
    "doge": "dogecoin",
    "usdc": "usd-coin",
    "link": "chainlink",
    "dot": "polkadot",
}


def main():
    parser = argparse.ArgumentParser(description="Sync crypto logos from CoinGecko")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    parser.add_argument("--symbols", type=str, default="", help="Only these short symbols, comma-separated (e.g. BTC,ETH,SOL,XRP)")
    args = parser.parse_args()

    filter_symbols = None
    if args.symbols:
        filter_symbols = {s.strip().upper().lower() for s in args.symbols.split(",") if s.strip()}
        print(f"Filter: only symbols {sorted(filter_symbols)}")

    logos_dir = api_dir / "uploads" / "crypto_logos"
    logos_dir.mkdir(parents=True, exist_ok=True)
    print(f"Logos directory: {logos_dir}")

    db = SessionLocal()
    try:
        instruments = (
            db.query(MarketDataInstrument)
            .filter(
                MarketDataInstrument.asset_class == "crypto",
                MarketDataInstrument.is_active == "true",
            )
            .order_by(MarketDataInstrument.symbol)
            .all()
        )
        if filter_symbols:
            def _short_sym(inst):
                raw = (inst.symbol or "").strip().upper()
                return (raw[:-4] if raw.endswith("USDT") and len(raw) > 4 else raw).lower()
            instruments = [i for i in instruments if _short_sym(i) in filter_symbols]
            print(f"Filtered to {len(instruments)} instrument(s)")
        if not instruments:
            print("No active crypto instruments in database. Exiting.")
            return

        print(f"Fetching CoinGecko coin list ({len(instruments)} cryptos to match)...")
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            list_resp = client.get(COINGECKO_LIST_URL)
            list_resp.raise_for_status()
            coins = list_resp.json()

        # Build map: symbol_lower -> list of {id, name, symbol}
        by_symbol = {}
        for c in coins:
            sym = (c.get("symbol") or "").strip().lower()
            if not sym:
                continue
            if sym not in by_symbol:
                by_symbol[sym] = []
            by_symbol[sym].append({"id": c.get("id"), "symbol": sym, "name": (c.get("name") or "").strip()})

        downloaded = 0
        skipped_exists = 0
        skipped_no_match = 0
        failures = 0

        for inst in instruments:
            raw = (inst.symbol or "").strip().upper()
            if not raw:
                print(f"  Skip (empty symbol): id={inst.id}")
                skipped_no_match += 1
                continue
            # Normalize: BTCUSDT -> BTC for CoinGecko match
            symbol_short = raw[:-4] if raw.endswith("USDT") and len(raw) > 4 else raw
            symbol_lower = symbol_short.lower()
            filename = f"{symbol_lower}.png"
            rel_path = f"crypto_logos/{filename}"
            local_path = logos_dir / filename

            if local_path.exists() and not args.force:
                if inst.logo_filename != rel_path:
                    inst.logo_filename = rel_path
                    db.commit()
                    print(f"  Already exists, updated DB: {symbol_short} -> {rel_path}")
                else:
                    print(f"  Already exists: {symbol_short}")
                skipped_exists += 1
                continue

            candidates = by_symbol.get(symbol_lower)
            if not candidates:
                # Try by name (e.g. "Bitcoin" -> bitcoin)
                name_lower = (inst.name or "").strip().lower().replace(" ", "-")
                if name_lower:
                    for c in coins:
                        cid = (c.get("id") or "").strip().lower()
                        if cid == name_lower or cid.replace("-", "") == name_lower.replace("-", ""):
                            candidates = [{"id": c.get("id"), "symbol": (c.get("symbol") or "").lower(), "name": (c.get("name") or "")}]
                            break
            if not candidates:
                print(f"  Skipped (no CoinGecko match): {symbol_short} / {inst.name}")
                skipped_no_match += 1
                continue

            preferred = PREFERRED_IDS.get(symbol_lower)
            chosen = None
            if preferred:
                for c in candidates:
                    if (c.get("id") or "").lower() == preferred:
                        chosen = c["id"]
                        break
            if chosen is None:
                chosen = candidates[0]["id"]
            coingecko_id = chosen
            if not coingecko_id:
                print(f"  Skipped (no id): {symbol_short}")
                skipped_no_match += 1
                continue

            time.sleep(DELAY_BETWEEN_COINS)
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                    coin_resp = client.get(f"{COINGECKO_COIN_URL}/{coingecko_id}")
                    coin_resp.raise_for_status()
                    data = coin_resp.json()
                image_data = data.get("image") or {}
                logo_url = image_data.get("small") or image_data.get("thumb") or image_data.get("large")
                if not logo_url:
                    print(f"  Skipped (no image URL): {symbol_short} / {coingecko_id}")
                    failures += 1
                    continue

                img_resp = httpx.get(logo_url, timeout=REQUEST_TIMEOUT)
                img_resp.raise_for_status()
                logos_dir.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(img_resp.content)

                inst.logo_filename = rel_path
                db.commit()
                print(f"  Downloaded: {symbol_short} -> {rel_path}")
                downloaded += 1
            except Exception as e:
                print(f"  Failure: {symbol_short} / {coingecko_id} -> {e}")
                failures += 1

        print("")
        print(f"Done. Downloaded: {downloaded}, Already exists: {skipped_exists}, Not matched: {skipped_no_match}, Failures: {failures}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
    sys.exit(0)
