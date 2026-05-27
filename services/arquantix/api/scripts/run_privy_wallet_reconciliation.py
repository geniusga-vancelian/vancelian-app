#!/usr/bin/env python3
"""Job de réconciliation ledger Privy ↔ on-chain (person scope ou batch futur)."""
from __future__ import annotations

import argparse
import json
import sys
import uuid

from database import SessionLocal
from services.privy_wallet.ledger_phantom_repair import void_untrusted_ledger_entries
from services.privy_wallet.reconciliation_service import run_person_wallet_reconciliation


def main() -> int:
    parser = argparse.ArgumentParser(description="Réconciliation soldes Privy wallet")
    parser.add_argument("--person-id", required=True, help="UUID person_id")
    parser.add_argument("--no-auto-heal", action="store_true", help="Compare only, no backfill")
    parser.add_argument(
        "--void-phantoms",
        action="store_true",
        help="Annule les crédits simulate (0xsim…) avant réconciliation",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Avec --void-phantoms : applique les void (sinon dry-run)",
    )
    args = parser.parse_args()

    person_uuid = uuid.UUID(args.person_id)
    db = SessionLocal()
    try:
        if args.void_phantoms:
            actions = void_untrusted_ledger_entries(
                db,
                person_id=person_uuid,
                dry_run=not args.apply,
            )
            print(json.dumps({"phantom_void_actions": actions}, indent=2))
            if args.apply and actions:
                db.commit()

        summary = run_person_wallet_reconciliation(
            db,
            person_id=person_uuid,
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
