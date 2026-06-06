#!/usr/bin/env python3
"""Audit prod lecture seule — réconciliation compte crypto multi-couches."""
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
    parser = argparse.ArgumentParser(description="Audit réconciliation crypto personne (lecture seule)")
    parser.add_argument("--email", required=True, help="Email client (ex. gaelitier@gmail.com)")
    parser.add_argument(
        "--prepare-fixes",
        action="store_true",
        help="Liste les correctifs safe idempotents (dry-run uniquement, aucune écriture)",
    )
    parser.add_argument(
        "--execute-safe-fixes",
        action="store_true",
        help="INTERDIT sans Go explicite — non implémenté en prod automatique",
    )
    args = parser.parse_args()

    if args.execute_safe_fixes:
        print(json.dumps({"error": "execute-safe-fixes désactivé — Go explicite requis via swap maintenance ciblée"}))
        sys.exit(2)

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
