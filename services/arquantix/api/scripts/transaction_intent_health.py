#!/usr/bin/env python3
"""
Santé transaction_intents — stale TTL + agrégats (Phase 8).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.transaction_intent_health --dry-run
    python3 -m scripts.transaction_intent_health --no-dry-run
    python3 -m scripts.transaction_intent_health --dry-run --person-id <UUID>
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
from services.transaction_intents.transaction_intent_health import (
    build_admin_health_payload,
    reconcile_stale_intents,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Santé transaction_intents (Phase 8)")
    parser.add_argument("--person-id", default=None, help="Limiter stale à une person")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Aucune écriture discrepancies (défaut)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Persiste discrepancies intent stale uniquement",
    )
    parser.add_argument("--limit", type=int, default=500, help="Max intents stale scannés")
    args = parser.parse_args()

    dry_run = not args.no_dry_run
    person_id = uuid.UUID(args.person_id) if args.person_id else None

    db = SessionLocal()
    try:
        health = build_admin_health_payload(db)
        stale_report = reconcile_stale_intents(
            db,
            dry_run=dry_run,
            person_id=person_id,
            limit=args.limit,
        )
        if not dry_run:
            db.commit()
        else:
            db.rollback()

        out = {"health": health, "stale_reconcile": stale_report}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1 if stale_report.get("stale_detected") else 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
