"""Forensic read-only — dernier rééquilibrage Crypto Majors."""
from __future__ import annotations

import json
import traceback
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
PORTFOLIO_ID = UUID("ab4ae920-f3e8-481b-8f82-a41a81d5779d")


def _audit_events(audit: Any) -> list[dict]:
    if not isinstance(audit, list):
        return []
    return [e for e in audit if isinstance(e, dict)]


def _swap_row(swap: PersonWalletSwap) -> dict[str, Any]:
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
        "failure_phase": getattr(swap, "failure_phase", None),
        "error_code": getattr(swap, "error_code", None),
        "bundle_context": ctx,
        "failures": failures,
        "audit_tail": events[-6:],
    }


def main() -> None:
    db = SessionLocal()
    try:
        report: dict[str, Any] = {
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "portfolio_id": str(PORTFOLIO_ID),
            "portfolio_name": "Crypto Majors",
        }

        guard = find_active_portfolio_financial_operation(db, portfolio_id=PORTFOLIO_ID)
        report["active_financial_guard"] = None if guard is None else {
            "operation_type": guard.operation_type,
            "execution_id": str(guard.execution_id),
            "status": guard.status,
        }
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
                ORDER BY created_at DESC
                LIMIT 12
                """
            ),
            {
                "entity_type": ENTITY_TYPE_V3_REBALANCE,
                "portfolio": str(PORTFOLIO_ID),
            },
        ).mappings().all()
        report["v3_audit_timeline"] = [
            {
                "action": r["action"],
                "entity_id": r["entity_id"],
                "created_at": r["created_at"],
                "v3_status": (r["metadata"] or {}).get("v3_status"),
                "sell_results": (r["metadata"] or {}).get("sell_results"),
                "buy_results": (r["metadata"] or {}).get("buy_results"),
                "trigger": (r["metadata"] or {}).get("trigger"),
            }
            for r in audits
        ]

        intents = db.execute(
            text(
                """
                SELECT id::text, product_type, status, created_at::text, updated_at::text,
                       metadata_json->>'batch_id' AS batch_id,
                       metadata_json->>'v3_status' AS v3_status,
                       metadata_json->>'error' AS error,
                       metadata_json->'sell_results' AS sell_results,
                       metadata_json->'buy_results' AS buy_results
                FROM transaction_intents
                WHERE metadata_json->>'portfolio_id' = :pid
                  AND product_type = 'bundle_portfolio_rebalance_v1'
                ORDER BY created_at DESC
                LIMIT 5
                """
            ),
            {"pid": str(PORTFOLIO_ID)},
        ).mappings().all()
        report["recent_rebalance_intents"] = [dict(r) for r in intents]

        swaps = (
            db.query(PersonWalletSwap)
            .filter(PersonWalletSwap.person_id == PERSON_ID)
            .order_by(PersonWalletSwap.created_at.desc())
            .limit(30)
            .all()
        )
        majors_swaps = []
        for swap in swaps:
            ctx = bundle_context_from_swap_audit(swap) or {}
            if str(ctx.get("portfolio_id") or "") != str(PORTFOLIO_ID):
                continue
            if ctx.get("bundle_action") == "rebalance_v3" or "rebal" in str(
                ctx.get("leg_id") or "",
            ):
                majors_swaps.append(_swap_row(swap))
        report["recent_rebalance_swaps"] = majors_swaps

        try:
            from services.portfolio_engine.bundles.rebalancing_portfolio import (
                preview_rebalancing_portfolio,
            )

            report["current_preview"] = preview_rebalancing_portfolio(
                db, client_id=CLIENT_ID, portfolio_id=PORTFOLIO_ID,
            )
        except Exception as exc:
            report["current_preview"] = {
                "error": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc()[-1500:],
            }
    finally:
        db.close()

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
