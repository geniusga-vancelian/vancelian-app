#!/usr/bin/env python3
"""Maintenance sessions swap LI.FI — expiration + réconciliation SUBMITTED/partielle."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID


def _bootstrap() -> Path:
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    os.chdir(api_dir)
    return api_dir


def main() -> None:
    _bootstrap()
    parser = argparse.ArgumentParser(description="Maintenance swap sessions LI.FI")
    parser.add_argument("--execute", action="store_true", help="Appliquer les changements (défaut: dry-run)")
    parser.add_argument(
        "--swap-id",
        dest="swap_id",
        metavar="UUID",
        help="Dry-run / exécution ciblée sur un swap (ex. 76830776-039d-48a3-9e58-df48b0b10f7e)",
    )
    args = parser.parse_args()

    import main as _main  # noqa: F401

    from database import SessionLocal
    from services.lifi.lifi_swap_reconciliation import settle_lifi_swap_idempotently
    from services.lifi.swap_session_maintenance import run_swap_session_maintenance

    db = SessionLocal()
    try:
        if args.swap_id:
            result = settle_lifi_swap_idempotently(
                db,
                UUID(str(args.swap_id)),
                dry_run=not args.execute,
            )
            payload = {
                "targeted": True,
                "swap_id": str(args.swap_id),
                "execute": bool(args.execute),
                "preview": result.preview,
                "action": result.action,
                "would_write": result.would_write,
                "status_before": result.status_before,
                "status_after": result.status_after,
            }
            print(json.dumps(payload, indent=2, default=str))
            return

        report = run_swap_session_maintenance(db, dry_run=not args.execute)
        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
