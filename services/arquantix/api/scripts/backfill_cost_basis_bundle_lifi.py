#!/usr/bin/env python3
"""Backfill cost basis V2 depuis swaps Li.FI bundle (legs internes).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.backfill_cost_basis_bundle_lifi
    python3 -m scripts.backfill_cost_basis_bundle_lifi --execute
    python3 -m scripts.backfill_cost_basis_bundle_lifi --execute --portfolio-id <UUID>
"""
from __future__ import annotations

import argparse
import json
import logging
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
from services.cost_basis.backfill_bundle_lifi import run_bundle_lifi_cost_basis_backfill


def _parse_uuid(value: str | None, label: str) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value).strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid {label}: {value}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill bundle Li.FI → cost_basis_executions")
    parser.add_argument("--execute", action="store_true", help="Persister les lignes manquantes")
    parser.add_argument("--person-id", type=str, default=None)
    parser.add_argument("--client-id", type=str, default=None)
    parser.add_argument("--portfolio-id", type=str, default=None)
    parser.add_argument("--asset", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--allow-onchain-resolve", action="store_true")
    parser.add_argument("--allow-mock-quote-amount", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    db = SessionLocal()
    try:
        result = run_bundle_lifi_cost_basis_backfill(
            db,
            dry_run=not args.execute,
            person_id=_parse_uuid(args.person_id, "person-id"),
            client_id=_parse_uuid(args.client_id, "client-id"),
            portfolio_id=_parse_uuid(args.portfolio_id, "portfolio-id"),
            asset=args.asset,
            limit=args.limit,
            allow_onchain_resolve=args.allow_onchain_resolve,
            allow_mock_quote_amount=args.allow_mock_quote_amount,
        )
        if args.execute:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.errors == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
