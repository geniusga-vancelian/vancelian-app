"""Audit read-only — opération bundle active (pilote)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from database import SessionLocal
from services.portfolio_engine.bundles.rebalance_executor import find_running_v3_rebalance_execution
from services.portfolio_engine.bundles.rebalancing_portfolio import get_active_bundle_operation

CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
PORTFOLIOS = (
    ("ab4ae920-f3e8-481b-8f82-a41a81d5779d", "Crypto Majors"),
    ("daea3720-e58e-410f-a796-3bbd541ac608", "Two Crypto Kings"),
)


def main() -> None:
    db = SessionLocal()
    report = {"at": datetime.now(timezone.utc).isoformat(), "portfolios": []}
    try:
        for pid, name in PORTFOLIOS:
            portfolio_id = UUID(pid)
            active = get_active_bundle_operation(
                db, client_id=CLIENT_ID, portfolio_id=portfolio_id,
            )
            running = find_running_v3_rebalance_execution(db, portfolio_id=pid)
            report["portfolios"].append(
                {
                    "name": name,
                    "portfolio_id": pid,
                    "active_operation": active,
                    "running_raw": running,
                },
            )
        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
