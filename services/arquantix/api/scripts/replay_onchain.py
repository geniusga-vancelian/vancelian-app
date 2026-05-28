#!/usr/bin/env python3
"""
Replay ERC20 Transfer logs sur une plage de blocs Base → raw_onchain_events.

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.replay_onchain --chain base --from-block 123 --to-block 456 --dry-run
    python3 -m scripts.replay_onchain --chain base --from-block 123 --to-block 456 --no-dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from database import SessionLocal
from services.onchain_indexer.block_range_replay import replay_block_range
from services.onchain_indexer.chain_config import resolve_chain_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay on-chain ERC20 Transfer (Base pilote)")
    parser.add_argument("--chain", default="base", help="Réseau (base)")
    parser.add_argument("--from-block", type=int, required=True)
    parser.add_argument("--to-block", type=int, required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Prévisualise sans écrire (défaut)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Insère uniquement dans raw_onchain_events",
    )
    parser.add_argument(
        "--block-chunk",
        type=int,
        default=2000,
        help="Taille des plages eth_getLogs (cap 10 sur Alchemy Free)",
    )
    parser.add_argument(
        "--wallet-address",
        action="append",
        default=[],
        help="Limiter au(x) wallet(s) cible(s) — réduit les appels RPC",
    )
    parser.add_argument(
        "--assets",
        default="",
        help="CSV symboles ERC20 à scanner (ex: USDC,EURC). Vide = tous.",
    )
    args = parser.parse_args()

    dry_run = not args.no_dry_run
    try:
        chain_id = resolve_chain_id(args.chain)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        wallets = {w.strip().lower() for w in args.wallet_address if w.strip()}
        assets = [a.strip() for a in args.assets.split(",") if a.strip()] or None

        result = replay_block_range(
            db,
            chain_id=chain_id,
            from_block=args.from_block,
            to_block=args.to_block,
            dry_run=dry_run,
            block_chunk=args.block_chunk,
            wallet_addresses=wallets or None,
            assets=assets,
        )
        if not dry_run:
            db.commit()
        else:
            db.rollback()

        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 1 if result.errors else 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
