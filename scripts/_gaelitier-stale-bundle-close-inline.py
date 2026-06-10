"""Clôture intents bundle zombies — reconcile-stale Kings + Majors (gaelitier)."""
from __future__ import annotations

import json
import os
from uuid import UUID

from database import SessionLocal
from services.portfolio_engine.bundles.rebalancing_portfolio import (
    _compute_drift_and_plan,
    get_active_bundle_operation,
    reconcile_stale_bundle_portfolio_state,
)

CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
KINGS_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")
MAJORS_ID = UUID("ab4ae920-f3e8-481b-8f82-a41a81d5779d")


def _apply_mode() -> bool:
    return os.getenv("BUNDLE_STALE_CLOSE_APPLY", "").strip().lower() in ("1", "true", "yes", "on")


def _force_close_signable_v3_legacy(db, *, client_id: UUID, portfolio_id: UUID) -> dict | None:
    """Filet immédiat — expire swaps signature pending et terminalise V3 (sans nouveau deploy)."""
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.lifi.swap_repository import PersonWalletSwapRepository
    from services.portfolio_engine.bundles.rebalance_executor import (
        _force_terminalize_running_snapshot,
        _release_v3_rebalance_guard,
        _results_from_metadata,
        find_running_v3_rebalance_execution,
        reconcile_running_v3_rebalance_execution,
    )

    pid = str(portfolio_id)
    running = find_running_v3_rebalance_execution(db, portfolio_id=pid)
    if running is None:
        return None

    sell = _results_from_metadata(running.get("sell_results") or [])
    buy = _results_from_metadata(running.get("buy_results") or [])
    repo = PersonWalletSwapRepository()
    for row in sell + buy:
        if row.status != "pending" or not row.swap_id:
            continue
        if row.error not in (
            "awaiting_client_signature",
            "awaiting_wallet_signature",
            "awaiting_confirmation",
        ):
            continue
        try:
            swap = db.query(PersonWalletSwap).filter(
                PersonWalletSwap.id == UUID(str(row.swap_id)),
            ).first()
        except ValueError:
            continue
        if swap is None:
            row.status = "expired"
            continue
        if swap.status in (
            SwapSessionStatus.AWAITING_SIGNATURE.value,
            SwapSessionStatus.QUOTE_RECEIVED.value,
            SwapSessionStatus.PENDING.value,
        ):
            swap.status = SwapSessionStatus.EXPIRED.value
            repo.append_audit(swap, {"event": "ops_force_signable_close"})
            db.add(swap)
            row.status = "expired"
            row.error = "client_signature_stale"

    _drift, plan = _compute_drift_and_plan(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    terminal = reconcile_running_v3_rebalance_execution(
        db,
        portfolio_id=pid,
        client_id=client_id,
        drift_rebalance_plan=plan,
        auto_progress=False,
    )
    if terminal is not None:
        return terminal

    if find_running_v3_rebalance_execution(db, portfolio_id=pid) is None:
        return None

    payload = {
        **running,
        "sell_results": [r.to_dict() for r in sell],
        "buy_results": [r.to_dict() for r in buy],
    }
    terminal = _force_terminalize_running_snapshot(
        db,
        running=payload,
        actor_id="ops-gaelitier-force-signable",
        extra={"ops_force_signable_close": True},
    )
    _release_v3_rebalance_guard(db, portfolio_id=pid, terminal=terminal)
    return terminal


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
                forced = _force_close_signable_v3_legacy(
                    db, client_id=CLIENT_ID, portfolio_id=pid,
                )
                if forced is not None:
                    entry["force_signable_v3"] = {
                        "v3_status": forced.get("v3_status"),
                    }
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
