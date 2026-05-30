#!/usr/bin/env python3
"""
Rapport dry-run des écarts transaction_intents (Phase 1).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.transaction_intent_gap_report
    python3 -m scripts.transaction_intent_gap_report --person-id <UUID>
    python3 -m scripts.transaction_intent_gap_report --person-limit 50
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
from services.transaction_intents.transaction_intent_reconciliation import build_gap_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapport dry-run gaps transaction_intents")
    parser.add_argument("--person-id", default=None, help="Limiter à une personne")
    parser.add_argument("--person-limit", type=int, default=200, help="Max personnes scannées")
    parser.add_argument("--stale-hours", type=int, default=24, help="Fenêtre stale partial")
    args = parser.parse_args()

    person_id = uuid.UUID(args.person_id) if args.person_id else None
    db = SessionLocal()
    try:
        payload = build_gap_report(
            db,
            person_id=person_id,
            person_limit=args.person_limit,
            stale_hours=args.stale_hours,
        )
        print(json.dumps(payload, indent=2, default=str))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
