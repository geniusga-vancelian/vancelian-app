"""Audit échec dépôt bundle récent — gaelitier Kings."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text

from database import SessionLocal
from services.portfolio_engine.bundles.rebalance_executor import (
    ACTION_V3_TERMINAL,
    ENTITY_TYPE_V3_REBALANCE,
    find_running_v3_rebalance_execution,
)
from services.portfolio_engine.bundles.rebalancing_portfolio import (
    get_active_bundle_operation,
    reconcile_stale_bundle_portfolio_state,
)

CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
PERSON_ID = UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
KINGS_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")
DEPOSIT_TX = os.environ.get("AUDIT_DEPOSIT_TX", "a74b22b9-f16a-466b-886c-7b971068cdb7")


def main() -> None:
    db = SessionLocal()
    report: dict = {"at": datetime.now(timezone.utc).isoformat()}
    try:
        report["flags"] = {
            k: os.getenv(k)
            for k in (
                "BUNDLE_V3_DEPOSIT_FLOW_ENABLED",
                "BUNDLE_V3_DEPOSIT_WORKER_ENABLED",
                "BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED",
                "PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED",
            )
        }
        report["active_operation"] = get_active_bundle_operation(
            db, client_id=CLIENT_ID, portfolio_id=KINGS_ID,
        )
        report["running_v3"] = find_running_v3_rebalance_execution(
            db, portfolio_id=str(KINGS_ID),
        )

        report["recent_intents"] = [
            dict(r)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, product_type, status, operation_type, created_at,
                           metadata_json
                    FROM transaction_intents
                    WHERE person_id = :person
                      AND created_at >= NOW() - INTERVAL '3 hours'
                    ORDER BY created_at DESC
                    LIMIT 15
                    """
                ),
                {"person": str(PERSON_ID)},
            ).mappings().all()
        ]

        report["v3_outbox"] = [
            dict(r)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, status, attempt_count, max_attempts, last_error,
                           created_at, processed_at, next_retry_at, intent_id::text,
                           payload_json
                    FROM transaction_outbox
                    WHERE event_type = 'bundle.v3_rebalance_requested'
                      AND payload_json->>'portfolio_id' = :pid
                      AND created_at >= NOW() - INTERVAL '3 hours'
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                ),
                {"pid": str(KINGS_ID)},
            ).mappings().all()
        ]

        report["v3_audits"] = [
            {
                "action": r["action"],
                "entity_id": r["entity_id"],
                "v3_status": (r["metadata"] or {}).get("v3_status"),
                "batch_id": (r["metadata"] or {}).get("batch_id"),
                "sell_results": (r["metadata"] or {}).get("sell_results"),
                "buy_results": (r["metadata"] or {}).get("buy_results"),
                "created_at": str(r["created_at"]),
            }
            for r in db.execute(
                text(
                    """
                    SELECT action, entity_id::text, metadata, created_at
                    FROM pe_audit_events
                    WHERE entity_type = :entity
                      AND metadata->>'portfolio_id' = :pid
                      AND created_at >= NOW() - INTERVAL '3 hours'
                    ORDER BY created_at ASC
                    """
                ),
                {"entity": ENTITY_TYPE_V3_REBALANCE, "pid": str(KINGS_ID)},
            ).mappings().all()
        ]

        report["pfo"] = [
            dict(r)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, status, operation_type, execution_id::text,
                           released_at, expires_at, created_at
                    FROM portfolio_financial_operations
                    WHERE portfolio_id = :pid
                      AND created_at >= NOW() - INTERVAL '3 hours'
                    ORDER BY created_at DESC
                    """
                ),
                {"pid": str(KINGS_ID)},
            ).mappings().all()
        ]

        from services.product_locks.global_user_transaction_lock import (
            find_active_global_user_transaction_lock,
        )

        active_lock = find_active_global_user_transaction_lock(db, person_id=PERSON_ID)
        report["global_lock"] = (
            {
                "id": str(active_lock.id),
                "intent_id": str(active_lock.intent_id) if active_lock.intent_id else None,
                "status": active_lock.status,
                "lock_key": active_lock.lock_key,
                "expires_at": str(active_lock.expires_at),
            }
            if active_lock is not None
            else None
        )

        report["recent_swaps"] = [
            dict(r)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, status, from_asset, to_asset, amount_in,
                           error_message, created_at, updated_at
                    FROM person_wallet_swaps
                    WHERE person_id = :person
                      AND created_at >= NOW() - INTERVAL '3 hours'
                    ORDER BY created_at DESC
                    LIMIT 20
                    """
                ),
                {"person": str(PERSON_ID)},
            ).mappings().all()
        ]

        report["deposit_tx"] = DEPOSIT_TX
        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
