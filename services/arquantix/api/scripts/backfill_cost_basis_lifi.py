#!/usr/bin/env python3
"""Backfill idempotent cost basis V2 depuis swaps Li.FI historiques confirmés.

Usage (depuis ``services/arquantix/api``)::

    # Dry-run (défaut) — aucune écriture
    python3 -m scripts.backfill_cost_basis_lifi

    # Appliquer les ingestions manquantes
    python3 -m scripts.backfill_cost_basis_lifi --execute

    # Filtres optionnels
    python3 -m scripts.backfill_cost_basis_lifi --execute \\
        --person-id <UUID> \\
        --client-id <UUID> \\
        --asset AAVE \\
        --limit 100

    # Si montants ledger/audit absents, autoriser résolution on-chain (prod prudent)
    python3 -m scripts.backfill_cost_basis_lifi --execute --allow-onchain-resolve
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
from services.cost_basis.backfill_lifi import run_lifi_cost_basis_backfill


def _parse_uuid(value: str | None, label: str) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value).strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid {label}: {value}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill cost_basis_executions from historical Li.FI swaps",
    )
    parser.add_argument("--person-id", type=str, default=None, help="Filtrer par person_id")
    parser.add_argument("--client-id", type=str, default=None, help="Filtrer par pe_client_id")
    parser.add_argument("--asset", type=str, default=None, help="Filtrer swaps touchant cet actif")
    parser.add_argument("--limit", type=int, default=None, help="Nombre max de swaps scannés")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Planifier sans écrire (défaut si --execute absent)",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Persister les lignes cost_basis_executions manquantes",
    )
    parser.add_argument(
        "--allow-onchain-resolve",
        action="store_true",
        help="Dernier recours : resolve_lifi_actual_receive_amount (RPC/API)",
    )
    parser.add_argument(
        "--allow-mock-quote",
        action="store_true",
        help="Autoriser montants mock en dev",
    )
    parser.add_argument("--pretty", action="store_true", default=True)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    dry_run = not args.execute

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    person_id = _parse_uuid(args.person_id, "person-id")
    client_id = _parse_uuid(args.client_id, "client-id")
    asset = args.asset.strip().upper() if args.asset else None

    db = SessionLocal()
    try:
        result = run_lifi_cost_basis_backfill(
            db,
            dry_run=dry_run,
            person_id=person_id,
            client_id=client_id,
            asset=asset,
            limit=args.limit,
            allow_onchain_resolve=args.allow_onchain_resolve,
            allow_mock_quote_amount=args.allow_mock_quote,
        )
        if not dry_run:
            db.commit()
        else:
            db.rollback()

        payload = result.to_dict()
        print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False, default=str))

        if result.errors > 0:
            return 2
        return 0
    except Exception as exc:
        db.rollback()
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
