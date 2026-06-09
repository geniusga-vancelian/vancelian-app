#!/usr/bin/env python3
"""
Tick observabilité DeFi — indexer + health + reconcile users (Phase 9–10).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.defi_observability_tick --dry-run
    python3 -m scripts.defi_observability_tick --no-dry-run
    python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480

Cron externe — voir docs/arquantix/DEFI_OBSERVABILITY_OPS_GO_LIVE.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from database import SessionLocal
from services.defi_observability.lock import release_defi_tick_lock, try_acquire_defi_tick_lock
from services.defi_observability.tick_service import (
    record_skipped_locked_tick,
    run_defi_observability_tick,
)


def _exit_code(summary: dict) -> int:
    status = summary.get("overall_status", "success")
    if status == "skipped_locked":
        return 0
    if status == "error":
        return 1
    if status in ("degraded", "timeout_degraded") or summary.get("alerts"):
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Tick observabilité DeFi (Phase 9–10)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Aucune écriture (défaut)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Écrit raw events, checkpoints, discrepancies, job_runs",
    )
    parser.add_argument("--max-users", type=int, default=25, help="Users récents à reconcilier")
    parser.add_argument("--user-hours", type=int, default=48, help="Fenêtre activité intent")
    parser.add_argument("--chain", default="base", help="Chaîne indexer")
    parser.add_argument(
        "--max-duration-seconds",
        type=int,
        default=None,
        help="Arrêt propre entre étapes si dépassé (timeout_degraded)",
    )
    parser.add_argument(
        "--skip-job-run",
        action="store_true",
        help="Ne pas persister defi_observability_job_runs",
    )
    args = parser.parse_args()

    dry_run = not args.no_dry_run
    lock_held = False
    db = SessionLocal()
    try:
        if not dry_run:
            if not try_acquire_defi_tick_lock(db):
                summary = record_skipped_locked_tick(
                    db,
                    persist_job_run=not args.skip_job_run,
                )
                db.commit()
                print(json.dumps(summary, indent=2, ensure_ascii=False))
                return 0
            lock_held = True

        summary = run_defi_observability_tick(
            db,
            dry_run=dry_run,
            max_users=args.max_users,
            user_hours=args.user_hours,
            chain=args.chain,
            persist_job_run=not args.skip_job_run,
            max_duration_seconds=args.max_duration_seconds,
        )
        if not dry_run:
            db.commit()
        else:
            db.rollback()

        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return _exit_code(summary)
    except Exception as exc:
        if not dry_run:
            try:
                db.commit()
            except Exception:
                db.rollback()
        else:
            db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if lock_held:
            try:
                release_defi_tick_lock(db)
            except Exception:
                pass
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
