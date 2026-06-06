#!/usr/bin/env python3
"""Audit final lecture seule — délègue à build_person_crypto_audit (doctrine v2)."""
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
    parser = argparse.ArgumentParser(description="Audit final réconciliation crypto (lecture seule, doctrine v2)")
    parser.add_argument("--email", required=True)
    parser.add_argument("--prepare-fixes", action="store_true")
    args = parser.parse_args()

    import main as _main  # noqa: F401

    from database import SessionLocal
    from services.audit.person_crypto_reconciliation import build_person_crypto_audit

    db = SessionLocal()
    try:
        report = build_person_crypto_audit(
            db,
            email=args.email.strip(),
            prepare_fixes=args.prepare_fixes,
        )
        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
