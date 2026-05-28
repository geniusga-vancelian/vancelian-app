#!/usr/bin/env python3
"""
Indexer continu Base → raw_onchain_events uniquement (Phase 6).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.run_onchain_indexer --chain base --once --dry-run
    python3 -m scripts.run_onchain_indexer --chain base --once --no-dry-run

Variables : ONCHAIN_INDEXER_BASE_* (voir docs/arquantix/ONCHAIN_INDEXER_BASE.md).
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
from services.onchain_indexer.chain_config import resolve_chain_id
from services.onchain_indexer.continuous_base_indexer import (
    IndexerConfigError,
    IndexerNotEnabledError,
    run_base_indexer_once,
)
from services.onchain_indexer.indexer_config import BaseIndexerConfig


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexer continu Base (raw_onchain_events)")
    parser.add_argument("--chain", default="base", help="Réseau (base)")
    parser.add_argument("--once", action="store_true", help="Un seul passage (requis)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Prévisualise sans écrire (défaut)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Écrit raw_onchain_events + checkpoint",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Autorise l'écriture même si ONCHAIN_INDEXER_BASE_ENABLED=false",
    )
    args = parser.parse_args()

    if not args.once:
        print("ERROR: --once est requis (pas de boucle daemon en Phase 6)", file=sys.stderr)
        return 2

    dry_run = not args.no_dry_run
    try:
        chain_id = resolve_chain_id(args.chain)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    cfg = BaseIndexerConfig.from_env()
    db = SessionLocal()
    try:
        result = run_base_indexer_once(
            db,
            chain_id=chain_id,
            dry_run=dry_run,
            config=cfg,
            force_write=args.force,
        )
        if not dry_run:
            db.commit()
        else:
            db.rollback()

        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 1 if result.errors else 0
    except (IndexerNotEnabledError, IndexerConfigError) as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
