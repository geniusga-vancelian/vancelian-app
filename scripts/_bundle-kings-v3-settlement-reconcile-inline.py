"""Réconciliation prod — settlement PE manquant + clôture RUNNING stale (Kings)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.allocation_settlement import (
    resolve_allocation_leg_settlement_amounts,
)
from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit
from services.portfolio_engine.bundle_execution.bundle_swap_pe_settlement import (
    SETTLEMENT_RECEIPT_EVENT,
    try_settle_confirmed_bundle_swap,
)
from services.portfolio_engine.bundle_execution.bundle_funding import resolve_bundle_cash_leg_available
from services.portfolio_engine.bundle_execution.bundle_cost_basis import reference_cost_basis_eur
from services.portfolio_engine.bundle_execution.pe_settlement import (
    apply_rebalance_buy_atoms,
    swap_confirmed,
)
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.rebalance_executor import (
    find_running_v3_rebalance_execution,
    force_terminalize_running_v3_rebalance_on_plan_drift,
)
from services.portfolio_engine.financial_operations.service import (
    find_active_portfolio_financial_operation,
)
from services.portfolio_engine.financial_operations.wiring import (
    release_bundle_rebalance_v3_portfolio_operation,
)
from services.portfolio_engine.portfolios.models import Portfolio
from sqlalchemy import text

PORTFOLIO_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")
PERSON_ID = UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
TARGET_SWAP_ID = UUID("86def914-dd55-4cf2-a36a-508601a063f7")


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


def _manual_apply_rebalance_buy(db, swap: PersonWalletSwap) -> dict:
    leg = leg_from_swap_audit(swap)
    if leg is None:
        raise RuntimeError("leg_missing")
    meta = leg.metadata or {}
    entry_id = UUID(str(meta["entry_instrument_id"]))
    target_id = UUID(str(meta["target_instrument_id"]))
    settlement = resolve_allocation_leg_settlement_amounts(
        db, swap, planned_amount_in=Decimal(str(swap.amount_in)),
    )
    cost_basis = reference_cost_basis_eur(db, str(swap.from_asset), settlement.amount_in)
    apply_rebalance_buy_atoms(
        db,
        portfolio_id=leg.portfolio_id,
        instrument_id=target_id,
        entry_instrument_id=entry_id,
        entry_spent=settlement.amount_in,
        crypto_received=settlement.amount_out,
        cost_basis_eur=cost_basis,
        ledger={
            "person_id": str(swap.person_id),
            "batch_id": leg.batch_id,
            "leg_id": leg.leg_id,
            "swap_id": str(swap.id),
            "from_asset": str(swap.from_asset),
            "to_asset": str(swap.to_asset),
        },
    )
    from services.lifi.swap_repository import PersonWalletSwapRepository

    PersonWalletSwapRepository.append_audit(
        swap,
        {
            "event": SETTLEMENT_RECEIPT_EVENT,
            "leg_id": leg.leg_id,
            "amount_in": str(settlement.amount_in),
            "amount_out": str(settlement.amount_out),
            "source": "manual_reconcile",
        },
    )
    PersonWalletSwapRepository.append_audit(
        swap,
        {"event": "bundle_pe_atoms_applied", "leg_id": leg.leg_id, "source": "manual_reconcile"},
    )
    return {
        "amount_in": str(settlement.amount_in),
        "amount_out": str(settlement.amount_out),
    }


def main() -> None:
    db = SessionLocal()
    report: dict = {"started_at": datetime.now(timezone.utc).isoformat()}
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.id == PORTFOLIO_ID).first()
        product = BundleOrchestrator._load_product(db, portfolio)
        entry_cfg = BundleOrchestrator._resolve_entry_config(product)
        entry_asset = str(entry_cfg.get("entry_asset_default") or "USDC")
        entry_inst = BundleOrchestrator._resolve_or_create_instrument(db, entry_asset).id

        report["before"] = {
            "atoms": _pe_atoms(db, PORTFOLIO_ID),
            "cash_available": str(
                resolve_bundle_cash_leg_available(
                    db, portfolio_id=PORTFOLIO_ID, entry_instrument_id=entry_inst,
                ),
            ),
            "running": find_running_v3_rebalance_execution(db, portfolio_id=str(PORTFOLIO_ID)),
            "financial_guard": find_active_portfolio_financial_operation(
                db, portfolio_id=PORTFOLIO_ID,
            ),
        }

        swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == TARGET_SWAP_ID).first()
        if swap is None:
            raise RuntimeError(f"swap_not_found:{TARGET_SWAP_ID}")

        report["swap"] = {
            "id": str(swap.id),
            "status": swap.status,
            "amount_in": str(swap.amount_in),
            "estimated_receive": str(swap.estimated_receive),
            "confirmed": swap_confirmed(swap),
        }

        settled = try_settle_confirmed_bundle_swap(db, swap, force=True)
        db.flush()
        db.refresh(swap)

        if not settled or not any(
            e.get("event") == SETTLEMENT_RECEIPT_EVENT
            for e in (swap.audit_log or [])
            if isinstance(e, dict)
        ):
            report["manual_apply"] = _manual_apply_rebalance_buy(db, swap)

        running = find_running_v3_rebalance_execution(db, portfolio_id=str(PORTFOLIO_ID))
        if running is not None:
            terminal = force_terminalize_running_v3_rebalance_on_plan_drift(
                db,
                portfolio_id=str(PORTFOLIO_ID),
                reason="manual_reconcile_post_settlement",
            )
            report["running_terminalized"] = terminal

        guard = find_active_portfolio_financial_operation(db, portfolio_id=PORTFOLIO_ID)
        if guard is not None:
            released = release_bundle_rebalance_v3_portfolio_operation(
                db,
                portfolio_id=PORTFOLIO_ID,
                execution_id=guard.execution_id,
                failed=False,
            )
            report["guard_released"] = released

        if os.environ.get("BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM") == "1":
            db.commit()
            report["committed"] = True
        else:
            db.rollback()
            report["committed"] = False
            report["mode"] = "dry_run"

        report["after"] = {
            "atoms": _pe_atoms(db, PORTFOLIO_ID),
            "cash_available": str(
                resolve_bundle_cash_leg_available(
                    db, portfolio_id=PORTFOLIO_ID, entry_instrument_id=entry_inst,
                ),
            ),
            "running": find_running_v3_rebalance_execution(db, portfolio_id=str(PORTFOLIO_ID)),
        }
        report["status"] = "ok"
        print(json.dumps(report, indent=2, default=str))
    except Exception as exc:
        db.rollback()
        report["status"] = "error"
        report["error"] = str(exc)
        print(json.dumps(report, indent=2, default=str))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
