#!/usr/bin/env python3
"""Job de réconciliation ledger Privy ↔ on-chain (person scope ou batch futur)."""
from __future__ import annotations

import argparse
import sys
import uuid

from database import SessionLocal
from services.privy_wallet.reconciliation_service import run_person_wallet_reconciliation


def main() -> int:
    parser = argparse.ArgumentParser(description="Réconciliation soldes Privy wallet")
    parser.add_argument("--person-id", required=True, help="UUID person_id")
    parser.add_argument("--no-auto-heal", action="store_true", help="Compare only, no backfill")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = run_person_wallet_reconciliation(
            db,
            person_id=uuid.UUID(args.person_id),
            auto_heal=not args.no_auto_heal,
        )
        db.commit()
        print(summary.message)
        if summary.unresolved_count or summary.mismatch_count:
            return 1
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
