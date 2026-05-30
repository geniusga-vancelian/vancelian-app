#!/usr/bin/env python3
"""
Backfill dry-run onchain_transaction_attempts depuis legacy (Phase 2).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.backfill_onchain_transaction_attempts --dry-run
    python3 -m scripts.backfill_onchain_transaction_attempts --person-id <UUID>
    python3 -m scripts.backfill_onchain_transaction_attempts --apply  # après migration 171
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
from services.transaction_attempts.reconciliation import apply_backfill, build_backfill_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill onchain_transaction_attempts (dry-run par défaut)"
    )
    parser.add_argument("--person-id", default=None, help="Limiter à une personne")
    parser.add_argument("--swap-limit", type=int, default=500)
    parser.add_argument("--vault-limit", type=int, default=500)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Rapport uniquement (défaut)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Écrire les attempts manquants (nécessite migration 171)",
    )
    args = parser.parse_args()

    person_id = uuid.UUID(args.person_id) if args.person_id else None
    dry_run = not args.apply

    db = SessionLocal()
    try:
        if dry_run:
            payload = build_backfill_report(
                db,
                person_id=person_id,
                swap_limit=args.swap_limit,
                vault_limit=args.vault_limit,
            )
        else:
            payload = apply_backfill(
                db,
                person_id=person_id,
                swap_limit=args.swap_limit,
                vault_limit=args.vault_limit,
            )
        db.commit()
        print(json.dumps(payload, indent=2, default=str))
        return 0 if payload.get("ready", False) else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
