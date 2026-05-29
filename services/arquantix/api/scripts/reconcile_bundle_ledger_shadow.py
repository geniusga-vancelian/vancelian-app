#!/usr/bin/env python3
"""Réconciliation read-only shadow ledger vs PE + Li.FI (Phase 4A.5).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.reconcile_bundle_ledger_shadow \\
        --person-id <UUID> \\
        --portfolio-id <UUID> \\
        [--batch-id <UUID>] \\
        [--pretty] \\
        [--fail-on-diff]
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
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Réconciliation shadow bundle_ledger_entries vs PE (read-only)",
    )
    parser.add_argument("--person-id", required=True, help="UUID person")
    parser.add_argument("--portfolio-id", required=True, help="UUID bundle portfolio")
    parser.add_argument("--batch-id", default=None, help="Filtrer événements par batch")
    parser.add_argument("--pretty", action="store_true", default=True)
    parser.add_argument(
        "--fail-on-diff",
        action="store_true",
        help="Exit code 2 si verdict DIFF ou INCOMPLETE",
    )
    args = parser.parse_args()

    person_id = UUID(args.person_id)
    portfolio_id = UUID(args.portfolio_id)
    batch_id = args.batch_id.strip() if args.batch_id else None

    db = SessionLocal()
    try:
        payload = reconcile_bundle_ledger_shadow(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False))
        if args.fail_on_diff and payload.get("verdict") in ("DIFF", "INCOMPLETE"):
            return 2
        return 0 if payload.get("verdict") == "MATCH" else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc), "read_only": True}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
