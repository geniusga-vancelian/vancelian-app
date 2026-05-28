#!/usr/bin/env python3
"""
Réconciliation wallet Privy — dry-run (Phase 3).

Usage (depuis ``services/arquantix/api``)::

    python3 scripts/reconcile_wallet.py --address 0x... --chain base --dry-run

    # Ingère les receipts connus dans raw_onchain_events (pas de correction balance) ::
    python3 scripts/reconcile_wallet.py --address 0x... --chain base --index-tx-hashes

Équivalent module::

    python3 -m scripts.reconcile_wallet --address 0x... --chain base --dry-run
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
from services.onchain_reconciliation.wallet_dry_run import build_wallet_reconcile_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Réconciliation wallet Privy ↔ on-chain (dry-run, pas de correction auto)",
    )
    parser.add_argument("--address", required=True, help="Adresse EVM du wallet Privy")
    parser.add_argument(
        "--chain",
        default="base",
        help="Réseau pilote (défaut: base → chain_id 8453)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Aucune écriture (défaut: true)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Autorise uniquement --index-tx-hashes (raw_onchain_events), jamais les balances",
    )
    parser.add_argument(
        "--index-tx-hashes",
        action="store_true",
        help="Indexe les tx des dépôts confirmés dans raw_onchain_events (nécessite RPC)",
    )
    args = parser.parse_args()

    dry_run = not args.no_dry_run
    if args.index_tx_hashes and dry_run:
        print(
            "WARN: --index-tx-hashes avec --dry-run n'écrit pas en base. "
            "Relancer avec --no-dry-run --index-tx-hashes pour indexer.",
            file=sys.stderr,
        )

    try:
        chain_id = resolve_chain_id(args.chain)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        report = build_wallet_reconcile_report(
            db,
            wallet_address=args.address,
            chain_id=chain_id,
            dry_run=dry_run,
            index_tx_hashes=args.index_tx_hashes,
        )
        if args.index_tx_hashes and not dry_run:
            db.commit()
        else:
            db.rollback()

        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))

        has_issues = bool(
            report.db_without_onchain_proof
            or report.onchain_without_db_ledger
            or any(
                d.get("within_dust_tolerance") == "False"
                for d in report.deltas_by_asset.values()
            )
        )
        return 1 if has_issues else 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
