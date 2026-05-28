#!/usr/bin/env python3
"""Reset local crypto bundle investment state — positions, swaps, locks, ledger.

Ne supprime pas les portfolios bundle ni les allocations cibles (templates / target_allocations).
Idempotent — safe to re-run.

Usage (from api/):
  python3 scripts/reset_local_crypto_bundle_investments.py
  python3 scripts/reset_local_crypto_bundle_investments.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from sqlalchemy import text

from database import SessionLocal


def reset(*, dry_run: bool) -> None:
    db = SessionLocal()
    try:
        bundle_portfolio_ids = [
            str(r[0])
            for r in db.execute(
                text(
                    """
                    SELECT id::text FROM pe_portfolios
                    WHERE portfolio_type = 'bundle_portfolio'
                    """
                )
            ).fetchall()
        ]
        if not bundle_portfolio_ids:
            print("  = Aucun bundle_portfolio — rien à nettoyer.")
            return

        print(f"  Bundle portfolios: {len(bundle_portfolio_ids)}")

        steps: list[tuple[str, str, dict]] = []

        steps.append(
            (
                "transaction_intents (bundle + lifi legs)",
                """
                DELETE FROM transaction_intents
                WHERE product_type IN ('bundle_invest', 'lifi_swap')
                   OR linked_table IN ('bundle_invest_lock', 'person_wallet_swaps')
                """,
                {},
            )
        )
        steps.append(
            (
                "person_wallet_deposits (swap / mock)",
                """
                DELETE FROM person_wallet_deposits
                WHERE transaction_kind = 'crypto_swap'
                   OR metadata_json::text ILIKE '%swap_id%'
                   OR metadata_json->>'source' LIKE 'lifi_%'
                """,
                {},
            )
        )
        steps.append(
            (
                "person_wallet_swaps",
                """
                DELETE FROM person_wallet_swaps
                """,
                {},
            )
        )
        steps.append(
            (
                "exchange_orders (bundle refs)",
                """
                DELETE FROM exchange_orders
                WHERE external_reference LIKE 'bundle-%'
                """,
                {},
            )
        )
        steps.append(
            (
                "pe_audit_events (bundle_investment)",
                """
                DELETE FROM pe_audit_events
                WHERE entity_type = 'bundle_investment'
                """,
                {},
            )
        )
        steps.append(
            (
                "crypto_positions (ledger exchange legacy)",
                """
                DELETE FROM crypto_positions
                """,
                {},
            )
        )
        steps.append(
            (
                "pe_portfolio_valuations (bundle)",
                """
                DELETE FROM pe_portfolio_valuations
                WHERE portfolio_id = ANY(CAST(:ids AS uuid[]))
                """,
                {"ids": bundle_portfolio_ids},
            )
        )
        steps.append(
            (
                "pe_position_atoms (bundle — cascade relations + valuations)",
                """
                DELETE FROM pe_position_atoms
                WHERE portfolio_id = ANY(CAST(:ids AS uuid[]))
                """,
                {"ids": bundle_portfolio_ids},
            )
        )

        for label, sql, params in steps:
            if dry_run:
                print(f"  ~ dry-run: {label}")
            else:
                result = db.execute(text(sql), params)
                print(f"  ✓ {label}: {result.rowcount} row(s)")

        if not dry_run:
            portfolios = db.execute(
                text(
                    """
                    SELECT id, metadata FROM pe_portfolios
                    WHERE portfolio_type = 'bundle_portfolio'
                    """
                )
            ).fetchall()
            cleared = 0
            for pid, metadata in portfolios:
                meta = dict(metadata or {})
                if "bundle_invest_lock" in meta:
                    meta.pop("bundle_invest_lock", None)
                    db.execute(
                        text("UPDATE pe_portfolios SET metadata = CAST(:meta AS jsonb) WHERE id = :id"),
                        {"id": pid, "meta": json.dumps(meta)},
                    )
                    cleared += 1
            print(f"  ✓ bundle_invest_lock cleared on {cleared} portfolio(s)")

            bal = db.execute(text("UPDATE person_wallet_balances SET balance = 0, available_balance = 0"))
            print(f"  ✓ person_wallet_balances reset: {bal.rowcount} row(s)")

            db.commit()
            print()
            print("  Reset bundle invest local terminé.")
        else:
            db.rollback()
            print()
            print("  DRY RUN — aucune modification.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset local crypto bundle investment artifacts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print("Reset investissements crypto bundle (local)...")
    if args.dry_run:
        print("  (dry run)")
    print()
    reset(dry_run=args.dry_run)
    print()
    print("Done.")


if __name__ == "__main__":
    main()
