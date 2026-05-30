#!/usr/bin/env python3
"""
Rapport dry-run des écarts onchain_transaction_attempts vs legacy (Phase 2).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.transaction_attempt_gap_report --dry-run
    python3 -m scripts.transaction_attempt_gap_report --person-id <UUID>
    python3 -m scripts.transaction_attempt_gap_report --person-limit 50
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
from services.transaction_attempts.reconciliation import build_gap_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rapport dry-run gaps onchain_transaction_attempts"
    )
    parser.add_argument("--person-id", default=None, help="Limiter à une personne")
    parser.add_argument("--person-limit", type=int, default=100, help="Max personnes scannées")
    parser.add_argument("--swap-limit", type=int, default=200)
    parser.add_argument("--vault-limit", type=int, default=200)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode lecture seule (défaut)",
    )
    args = parser.parse_args()

    person_id = uuid.UUID(args.person_id) if args.person_id else None
    db = SessionLocal()
    try:
        payload = build_gap_report(
            db,
            person_id=person_id,
            person_limit=args.person_limit,
            swap_limit=args.swap_limit,
            vault_limit=args.vault_limit,
        )
        db.commit()
        print(json.dumps(payload, indent=2, default=str))
        blocking = payload.get("summary", {}).get("blocking_gaps")
        if blocking is None:
            blocking = payload.get("summary", {}).get("total_gaps", 0)
        if not payload.get("ready", False):
            return 1
        return 1 if blocking > 0 else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
