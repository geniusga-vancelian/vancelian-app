#!/usr/bin/env python3
"""Validation panel rollout bundle ledger (Phase 4C).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.validate_bundle_ledger_rollout \\
        --portfolio-ids portfolios.txt \\
        [--apply-backfill] \\
        [--fail-on-diff] \\
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
from services.portfolio_engine.bundle_ledger.rollout import validate_rollout_panel


def _load_portfolio_ids(path: Path) -> list[UUID]:
    ids: list[UUID] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if "," in raw:
            raw = raw.split(",")[-1].strip()
        ids.append(UUID(raw))
    if not ids:
        raise ValueError(f"no_portfolio_ids_in_file: {path}")
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Validation panel rollout bundle ledger")
    parser.add_argument(
        "--portfolio-ids",
        required=True,
        help="Fichier texte — un portfolio UUID par ligne",
    )
    parser.add_argument(
        "--apply-backfill",
        action="store_true",
        help="Appliquer le backfill avant réconciliation",
    )
    parser.add_argument("--fail-on-diff", action="store_true")
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    portfolio_ids = _load_portfolio_ids(Path(args.portfolio_ids))
    db = SessionLocal()
    try:
        payload = validate_rollout_panel(
            db,
            portfolio_ids=portfolio_ids,
            apply_backfill=args.apply_backfill,
        )
        if args.apply_backfill:
            db.commit()

        print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False, default=str))

        if payload.get("errors"):
            return 2
        if args.fail_on_diff and payload.get("summary", {}).get("DIFF", 0) > 0:
            return 3
        if payload.get("rollout_status") == "ready":
            return 0
        return 1
    except Exception as exc:
        db.rollback()
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
