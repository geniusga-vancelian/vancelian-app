#!/usr/bin/env python3
"""Smoke validation allocation bundle Phase 5A.5.

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.smoke_bundle_allocation_phase5a \\
        --person-id <UUID> \\
        --portfolio-id <UUID> \\
        [--fund-amount 1000] \\
        [--execute-mock] \\
        [--pretty]

Read-only par défaut. ``--execute-mock`` requiert ``BUNDLE_LIFI_SYNC_MOCK=1`` et
``LIFI_SWAPS_MOCK=1``.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from database import SessionLocal
from services.portfolio_engine.bundle_execution.allocation_smoke import (
    run_smoke_bundle_allocation_phase5a,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke bundle allocation Phase 5A.5")
    parser.add_argument("--person-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--fund-amount", type=str, default="1000")
    parser.add_argument(
        "--execute-mock",
        action="store_true",
        help="Invest mock contrôlé (LIFI_SWAPS_MOCK + BUNDLE_LIFI_SYNC_MOCK requis)",
    )
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = run_smoke_bundle_allocation_phase5a(
            db,
            person_id=UUID(args.person_id),
            portfolio_id=UUID(args.portfolio_id),
            fund_amount=Decimal(args.fund_amount),
            execute_mock=args.execute_mock,
        )
        print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False, default=str))
        return 0 if result.get("status") == "PASS" else 1
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
