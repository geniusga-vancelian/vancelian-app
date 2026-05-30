#!/usr/bin/env python3
"""
Audit dry-run — mouvements de scope internes (Vault / Lombard / Bundle).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.internal_scope_movements_audit --dry-run --person-id <UUID>
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
from services.portfolio_engine.internal_scope_movements.audit import (
    build_internal_scope_audit_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit dry-run internal scope movements (read-only, no PE writes)"
    )
    parser.add_argument("--person-id", required=True, help="UUID person")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode lecture seule (défaut, seule option supportée)",
    )
    args = parser.parse_args()

    try:
        person_id = uuid.UUID(args.person_id.strip())
    except ValueError:
        print(json.dumps({"ready": False, "error": "person-id invalide"}, indent=2))
        return 1

    db = SessionLocal()
    try:
        report = build_internal_scope_audit_report(db, person_id=person_id)
        print(json.dumps(report, indent=2, default=str))
        blocking = report.get("summary", {}).get("gap_count", 0)
        return 1 if blocking > 0 else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
