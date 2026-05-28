#!/usr/bin/env python3
"""
Réconciliation agrégée par person_id (dry-run ou persistance anomalies uniquement).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.reconcile_user --person-id <UUID> --dry-run
    python3 -m scripts.reconcile_user --person-id <UUID> --no-dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from database import SessionLocal
from services.onchain_reconciliation.user_reconcile import build_user_reconcile_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Réconciliation utilisateur DeFi")
    parser.add_argument("--person-id", required=True, help="UUID person")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Aucune écriture (défaut)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Persiste uniquement reconciliation_discrepancies",
    )
    args = parser.parse_args()

    dry_run = not args.no_dry_run
    person_id = uuid.UUID(args.person_id)

    db = SessionLocal()
    try:
        report = build_user_reconcile_report(
            db,
            person_id=person_id,
            dry_run=dry_run,
            persist_discrepancies=not dry_run,
        )
        if not dry_run:
            db.commit()
        else:
            db.rollback()

        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 1 if report.anomalies else 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
