#!/usr/bin/env python3
"""Daily health check bundle ledger — read-only (Phase 4D).

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.check_bundle_ledger_health \\
        [--log-file /var/log/arquantix-api.log] \\
        [--since-hours 24] \\
        [--portfolio-limit 200] \\
        [--fail-on-alert] \\
        [--pretty]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from database import SessionLocal
from services.portfolio_engine.bundle_ledger.health import run_bundle_ledger_health_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily health check bundle ledger (read-only)")
    parser.add_argument(
        "--log-file",
        action="append",
        default=[],
        help="Fichier log API (répétable) pour métriques 24h",
    )
    parser.add_argument("--since-hours", type=int, default=24)
    parser.add_argument("--portfolio-limit", type=int, default=None)
    parser.add_argument("--fail-on-alert", action="store_true")
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = run_bundle_ledger_health_check(
            db,
            log_paths=args.log_file or None,
            since_hours=args.since_hours,
            portfolio_limit=args.portfolio_limit,
        )
        print(json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False, default=str))

        status = report.get("health_status", "ok")
        if args.fail_on_alert and status != "ok":
            return 2
        if status == "critical":
            return 3
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
