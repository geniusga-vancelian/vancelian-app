"""Clôture intents bundle zombies — reconcile-stale Kings + Majors (gaelitier)."""
from __future__ import annotations

import json
import os
from uuid import UUID

from database import SessionLocal
from services.portfolio_engine.bundles.rebalancing_portfolio import (
    get_active_bundle_operation,
    reconcile_stale_bundle_portfolio_state,
)

CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
KINGS_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")
MAJORS_ID = UUID("ab4ae920-f3e8-481b-8f82-a41a81d5779d")


def _apply_mode() -> bool:
    return os.getenv("BUNDLE_STALE_CLOSE_APPLY", "").strip().lower() in ("1", "true", "yes", "on")


def main() -> None:
    apply = _apply_mode()
    db = SessionLocal()
    report: dict = {"apply": apply, "portfolios": {}}
    try:
        for name, pid in (("kings", KINGS_ID), ("majors", MAJORS_ID)):
            before = get_active_bundle_operation(
                db, client_id=CLIENT_ID, portfolio_id=pid,
            )
            entry = {"before_active": before}
            if apply:
                entry["reconcile"] = reconcile_stale_bundle_portfolio_state(
                    db, client_id=CLIENT_ID, portfolio_id=pid,
                )
                entry["after_active"] = get_active_bundle_operation(
                    db, client_id=CLIENT_ID, portfolio_id=pid,
                )
            report["portfolios"][name] = entry
        if apply:
            db.commit()
        print(json.dumps(report, indent=2, default=str))
    except Exception as exc:
        db.rollback()
        report["error"] = str(exc)
        print(json.dumps(report, indent=2, default=str))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
