#!/usr/bin/env python3
"""Maintenance sessions swap LI.FI — expiration + réconciliation SUBMITTED."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


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
    args = parser.parse_args()

    import main as _main  # noqa: F401

    from database import SessionLocal
    from services.lifi.swap_session_maintenance import run_swap_session_maintenance

    db = SessionLocal()
    try:
        report = run_swap_session_maintenance(db, dry_run=not args.execute)
        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
