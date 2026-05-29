#!/usr/bin/env python3
"""Backfill idempotent ``bundle_ledger_entries`` (Phase 4B).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.backfill_bundle_ledger \\
        --person-id <UUID> \\
        --portfolio-id <UUID> \\
        [--batch-id <UUID>] \\
        [--dry-run] \\
        [--apply] \\
        [--pretty] \\
        [--fail-on-warning]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from database import SessionLocal
from services.portfolio_engine.bundle_ledger.backfill import run_backfill
from services.portfolio_engine.bundle_ledger.config import bundle_ledger_backfill_dry_run_default
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill bundle ledger (idempotent)")
    parser.add_argument("--person-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--batch-id", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Planifier sans écrire (défaut env)")
    mode.add_argument("--apply", action="store_true", help="Appliquer les entrées manquantes")
    parser.add_argument("--pretty", action="store_true", default=True)
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--reconcile-after", action="store_true", default=True)
    args = parser.parse_args()

    person_id = UUID(args.person_id)
    portfolio_id = UUID(args.portfolio_id)
    batch_id = args.batch_id.strip() if args.batch_id else None

    dry_run = not args.apply
    if not args.apply and not args.dry_run:
        dry_run = bundle_ledger_backfill_dry_run_default()

    db = SessionLocal()
    try:
        result = run_backfill(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            dry_run=dry_run,
        )
        if not dry_run:
            db.commit()

        payload = result.to_dict()
        if args.reconcile_after:
            payload["reconciliation"] = reconcile_bundle_ledger_shadow(
                db,
                person_id=person_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
            )

        print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False, default=str))

        if args.fail_on_warning and payload.get("warnings"):
            return 2
        if not dry_run and payload.get("reconciliation", {}).get("verdict") == "DIFF":
            return 3
        return 0
    except Exception as exc:
        db.rollback()
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
