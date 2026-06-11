"""Forensic read-only — dernier rééquilibrage Kings (batch 0d8f7fcd…)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from database import SessionLocal
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundles.rebalance_executor import (
    ENTITY_TYPE_V3_REBALANCE,
    find_running_v3_rebalance_execution,
    find_latest_terminal_v3_rebalance_for_portfolio,
)
from services.portfolio_engine.financial_operations import (
    find_active_portfolio_financial_operation,
)
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit
from sqlalchemy import text

CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
PERSON_ID = UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
PORTFOLIO_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")
BATCH_PREFIX = "0d8f7fcd"
EXECUTION_PREFIX = "64943c25"


def _audit_events(audit: Any) -> list[dict]:
    if not isinstance(audit, list):
        return []
    return [e for e in audit if isinstance(e, dict)]


def _swap_row(db, swap: PersonWalletSwap) -> dict[str, Any]:
    ctx = bundle_context_from_swap_audit(swap) or {}
    events = _audit_events(swap.audit_log)
    failures = [e for e in events if e.get("event") in ("swap_failure", "failure_recorded")]
    return {
        "swap_id": str(swap.id),
        "status": swap.status,
        "from_asset": swap.from_asset,
        "to_asset": swap.to_asset,
        "amount_in": str(swap.amount_in),
        "estimated_receive": str(swap.estimated_receive),
        "tx_hash": swap.tx_hash,
        "created_at": str(swap.created_at),
        "updated_at": str(swap.updated_at),
        "failure_phase": swap.failure_phase,
        "error_code": swap.error_code,
        "bundle_context": ctx,
        "failures": failures,
        "audit_tail": events[-8:],
    }


def main() -> None:
    db = SessionLocal()
    try:
        report: dict[str, Any] = {
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "portfolio_id": str(PORTFOLIO_ID),
            "batch_prefix": BATCH_PREFIX,
        }

        report["active_financial_guard"] = (
            None
            if find_active_portfolio_financial_operation(db, portfolio_id=PORTFOLIO_ID) is None
            else {
                "operation_type": find_active_portfolio_financial_operation(
                    db, portfolio_id=PORTFOLIO_ID,
                ).operation_type,
                "execution_id": str(
                    find_active_portfolio_financial_operation(
                        db, portfolio_id=PORTFOLIO_ID,
                    ).execution_id,
                ),
            }
        )
        report["running_v3"] = find_running_v3_rebalance_execution(
            db, portfolio_id=str(PORTFOLIO_ID),
        )
        report["latest_terminal_v3"] = find_latest_terminal_v3_rebalance_for_portfolio(
            db, portfolio_id=str(PORTFOLIO_ID),
        )

        audits = db.execute(
            text(
                """
                SELECT action, entity_id::text, created_at::text, metadata
                FROM pe_audit_events
                WHERE entity_type = :entity_type
                  AND metadata->>'portfolio_id' = :portfolio
                  AND (
                    metadata->>'batch_id' LIKE :batch
                    OR entity_id::text LIKE :exec
                  )
                ORDER BY created_at ASC
                """
            ),
            {
                "entity_type": ENTITY_TYPE_V3_REBALANCE,
                "portfolio": str(PORTFOLIO_ID),
                "batch": f"{BATCH_PREFIX}%",
                "exec": f"{EXECUTION_PREFIX}%",
            },
        ).mappings().all()
        report["v3_audit_timeline"] = [
            {
                "action": r["action"],
                "entity_id": r["entity_id"],
                "created_at": r["created_at"],
                "v3_status": (r["metadata"] or {}).get("v3_status"),
                "buy_results": (r["metadata"] or {}).get("buy_results"),
                "sell_results": (r["metadata"] or {}).get("sell_results"),
            }
            for r in audits
        ]

        swaps = (
            db.query(PersonWalletSwap)
            .filter(PersonWalletSwap.person_id == PERSON_ID)
            .order_by(PersonWalletSwap.created_at.desc())
            .limit(80)
            .all()
        )
        batch_swaps = []
        for swap in swaps:
            ctx = bundle_context_from_swap_audit(swap) or {}
            batch_id = str(ctx.get("batch_id") or "")
            exec_id = str(ctx.get("rebalance_execution_id") or "")
            if batch_id.startswith(BATCH_PREFIX) or exec_id.startswith(EXECUTION_PREFIX):
                batch_swaps.append(_swap_row(db, swap))
            else:
                for e in _audit_events(swap.audit_log):
                    if str(e.get("batch_id") or "").startswith(BATCH_PREFIX):
                        batch_swaps.append(_swap_row(db, swap))
                        break
        report["batch_swaps"] = batch_swaps

        intents = db.execute(
            text(
                """
                SELECT id::text, status, created_at::text, updated_at::text,
                       metadata_json->>'batch_id' AS batch_id,
                       metadata_json->>'v3_status' AS v3_status,
                       metadata_json->'legs' AS legs
                FROM transaction_intents
                WHERE metadata_json->>'portfolio_id' = :pid
                  AND (
                    metadata_json->>'batch_id' LIKE :batch
                    OR id::text LIKE :exec
                  )
                ORDER BY created_at DESC
                """
            ),
            {
                "pid": str(PORTFOLIO_ID),
                "batch": f"{BATCH_PREFIX}%",
                "exec": f"{EXECUTION_PREFIX}%",
            },
        ).mappings().all()
        report["intents"] = [dict(r) for r in intents]

        wallets = db.execute(
            text(
                """
                SELECT id::text, wallet_type, instrument_id::text, status, created_at::text
                FROM pe_wallet_containers
                WHERE portfolio_id = :pid
                ORDER BY created_at
                """
            ),
            {"pid": str(PORTFOLIO_ID)},
        ).mappings().all()
        report["virtual_wallets"] = [dict(r) for r in wallets]

        cash = db.execute(
            text(
                """
                SELECT a.symbol, pa.quantity::text, pa.available_quantity::text
                FROM pe_position_atoms pa
                JOIN pe_instruments i ON i.id = pa.instrument_id
                JOIN pe_assets a ON a.id = i.asset_id
                WHERE pa.portfolio_id = :pid AND pa.position_type = 'cash' AND pa.status = 'open'
                """
            ),
            {"pid": str(PORTFOLIO_ID)},
        ).mappings().all()
        report["cash_leg"] = [dict(r) for r in cash]

        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
