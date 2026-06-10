"""Audit ops — opération bundle active + réconciliation V3 (pilote Majors + Kings)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from database import SessionLocal
from services.portfolio_engine.bundle_execution.bundle_funding import resolve_bundle_cash_leg_available
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.rebalance_executor import find_running_v3_rebalance_execution
from services.portfolio_engine.bundles.rebalancing_portfolio import get_active_bundle_operation
from services.portfolio_engine.financial_operations.service import (
    find_active_portfolio_financial_operation,
)
from services.portfolio_engine.portfolios.models import Portfolio
from sqlalchemy import text

CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
PORTFOLIOS = (
    ("ab4ae920-f3e8-481b-8f82-a41a81d5779d", "Crypto Majors"),
    ("daea3720-e58e-410f-a796-3bbd541ac608", "Two Crypto Kings"),
)


def _pe_atoms(db, portfolio_id: UUID) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT a.symbol, pa.position_type, pa.quantity::text, pa.cost_basis::text
            FROM pe_position_atoms pa
            JOIN pe_instruments i ON i.id = pa.instrument_id
            JOIN pe_assets a ON a.id = i.asset_id
            WHERE pa.portfolio_id = :pid AND pa.status = 'open'
            ORDER BY pa.position_type, a.symbol
            """
        ),
        {"pid": str(portfolio_id)},
    ).mappings().all()
    return [dict(r) for r in rows]


def _reliability(active: dict, running_raw: dict | None, guard) -> dict:
    status = str(active.get("status") or "none")
    v3 = str(active.get("v3_status") or "")
    no_running = running_raw is None
    no_guard = guard is None
    idle = status == "none" and no_running
    active_ok = status == "active" and v3 in ("RUNNING", "QUEUED") and no_running is False
    deposit_queued = status == "active" and active.get("operation_type") == "v3_deposit_rebalance"
    signable = False
    if status == "active":
        legs = (active.get("sell_results") or []) + (active.get("buy_results") or [])
        signable = any(
            leg.get("status") == "pending"
            and leg.get("swap_id")
            and leg.get("error") in ("awaiting_client_signature", "awaiting_confirmation")
            for leg in legs
            if isinstance(leg, dict)
        )
    reliable = (idle and no_guard) or (active_ok and not signable and not active.get("plan_stale"))
    return {
        "reliable": reliable,
        "idle": idle,
        "active_legitimate": active_ok or deposit_queued,
        "awaiting_user_signature": signable,
        "plan_stale": bool(active.get("plan_stale")),
        "financial_guard_active": guard is not None,
        "running_v3_present": not no_running,
    }


def main() -> None:
    db = SessionLocal()
    report = {"at": datetime.now(timezone.utc).isoformat(), "portfolios": [], "all_reliable": True}
    try:
        for pid, name in PORTFOLIOS:
            portfolio_id = UUID(pid)
            active = get_active_bundle_operation(
                db, client_id=CLIENT_ID, portfolio_id=portfolio_id,
            )
            db.commit()
            running = find_running_v3_rebalance_execution(db, portfolio_id=pid)
            guard = find_active_portfolio_financial_operation(db, portfolio_id=portfolio_id)

            portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            cash_available = None
            atoms: list[dict] = []
            if portfolio is not None:
                product = BundleOrchestrator._load_product(db, portfolio)
                entry_cfg = BundleOrchestrator._resolve_entry_config(product)
                entry_asset = str(entry_cfg.get("entry_asset_default") or "USDC")
                entry_inst = BundleOrchestrator._resolve_or_create_instrument(db, entry_asset).id
                cash_available = str(
                    resolve_bundle_cash_leg_available(
                        db, portfolio_id=portfolio_id, entry_instrument_id=entry_inst,
                    ),
                )
                atoms = _pe_atoms(db, portfolio_id)

            rel = _reliability(active, running, guard)
            if not rel["reliable"]:
                report["all_reliable"] = False

            report["portfolios"].append(
                {
                    "name": name,
                    "portfolio_id": pid,
                    "reliability": rel,
                    "active_operation": active,
                    "running_raw": running,
                    "financial_guard": (
                        {
                            "operation_type": str(guard.operation_type),
                            "execution_id": str(guard.execution_id),
                        }
                        if guard is not None
                        else None
                    ),
                    "pe_atoms": atoms,
                    "cash_available": cash_available,
                },
            )
        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
