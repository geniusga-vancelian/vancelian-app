#!/usr/bin/env python3
"""Smoke test historique bundle ledger (Phase 4D).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.smoke_bundle_ledger_history \\
        --person-id <UUID> \\
        --portfolio-id <UUID> \\
        [--asset USDC] \\
        [--pretty]
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
from services.portfolio_engine.bundle_ledger.smoke import run_smoke_bundle_ledger_history


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke bundle ledger history (read-only)")
    parser.add_argument("--person-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--asset", default="USDC")
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = run_smoke_bundle_ledger_history(
            db,
            person_id=UUID(args.person_id),
            portfolio_id=UUID(args.portfolio_id),
            asset=args.asset.upper(),
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
