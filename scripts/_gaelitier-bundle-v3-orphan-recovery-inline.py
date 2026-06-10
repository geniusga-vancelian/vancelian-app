"""Recovery contrôlé — intent/lock/swap orphelins bundle V3 (gaelitier · Kings)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_transaction_global_lock import (
    release_bundle_transaction_global_lock_on_v3_terminal,
)
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    sync_bundle_transaction_rebalancing,
)
from services.portfolio_engine.bundles.rebalance_executor import (
    ENTITY_TYPE_V3_REBALANCE,
    ACTION_V3_TERMINAL,
    find_running_v3_rebalance_execution,
    force_terminalize_running_v3_rebalance_on_plan_drift,
)
from services.portfolio_engine.financial_operations.wiring import (
    release_active_bundle_portfolio_operation,
)
from services.product_locks.global_user_transaction_lock import (
    find_active_global_user_transaction_lock,
    release_global_user_transaction_lock,
)

PERSON_ID = UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
KINGS_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")
INTENT_ID = UUID("61ba1a78-ec3b-4134-b6e5-ab71237fdab2")
SWAP_ID = UUID("a36ac04f-6811-4216-9e9b-4ddd77170402")
BATCH_ID = "b2cc426d-a4ff-4e1a-9e6d-97a257adaffd"
DEPOSIT_EXEC_ID = "dc39eea3-7b3a-40b3-a995-ec4e870c70e0"


def _apply_mode() -> bool:
    return os.getenv("BUNDLE_V3_RECOVERY_APPLY", "").strip().lower() in ("1", "true", "yes", "on")


def _snapshot(db) -> dict:
    intent = db.query(TransactionIntent).filter(TransactionIntent.id == INTENT_ID).first()
    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == SWAP_ID).first()
    lock = find_active_global_user_transaction_lock(db, person_id=PERSON_ID)
    running = find_running_v3_rebalance_execution(db, portfolio_id=str(KINGS_ID))
    pfo = db.execute(
        text(
            """
            SELECT id::text, status, operation_type, execution_id::text, released_at
            FROM portfolio_financial_operations
            WHERE portfolio_id = :pid AND status = 'ACTIVE' AND released_at IS NULL
            """
        ),
        {"pid": str(KINGS_ID)},
    ).mappings().all()
    terminal_audits = db.execute(
        text(
            """
            SELECT entity_id::text, metadata, created_at
            FROM pe_audit_events
            WHERE entity_type = :entity AND action = :action
              AND metadata->>'portfolio_id' = :pid
            ORDER BY created_at DESC LIMIT 5
            """
        ),
        {"entity": ENTITY_TYPE_V3_REBALANCE, "action": ACTION_V3_TERMINAL, "pid": str(KINGS_ID)},
    ).mappings().all()
    return {
        "intent": (
            {
                "id": str(intent.id),
                "status": intent.status,
                "product_type": intent.product_type,
                "metadata": intent.metadata_json,
            }
            if intent
            else None
        ),
        "swap": (
            {
                "id": str(swap.id),
                "status": swap.status,
                "tx_hash": swap.tx_hash,
                "created_at": str(swap.created_at),
                "updated_at": str(swap.updated_at),
            }
            if swap
            else None
        ),
        "global_lock": (
            {
                "lock_id": str(lock.id),
                "intent_id": str(lock.intent_id),
                "expires_at": str(lock.expires_at),
            }
            if lock
            else None
        ),
        "running_v3": running,
        "active_pfo": [dict(r) for r in pfo],
        "recent_v3_terminal_audits": [
            {
                "entity_id": r["entity_id"],
                "v3_status": (r["metadata"] or {}).get("v3_status"),
                "created_at": str(r["created_at"]),
            }
            for r in terminal_audits
        ],
    }


def _expire_swap_if_stale(db, swap: PersonWalletSwap | None) -> dict | None:
    if swap is None:
        return None
    terminal_statuses = {
        SwapSessionStatus.CONFIRMED.value,
        SwapSessionStatus.FAILED.value,
        SwapSessionStatus.EXPIRED.value,
    }
    if swap.status in terminal_statuses:
        return {"skipped": True, "reason": "already_terminal", "status": swap.status}
    repo = PersonWalletSwapRepository()
    swap.status = SwapSessionStatus.EXPIRED.value
    repo.append_audit(
        swap,
        {
            "event": "recovery_expired",
            "reason": "bundle_v3_orphan_recovery",
            "batch_id": BATCH_ID,
        },
    )
    db.add(swap)
    return {"expired": True, "swap_id": str(swap.id), "new_status": swap.status}


def _finalize_intent_and_lock(db, *, terminal: dict) -> None:
    intent = db.query(TransactionIntent).filter(TransactionIntent.id == INTENT_ID).first()
    if intent is None:
        return
    sync_bundle_transaction_rebalancing(intent, result=terminal)
    release_bundle_transaction_global_lock_on_v3_terminal(
        db,
        intent_id=intent.id,
        v3_status=str(terminal.get("v3_status") or "FAILED"),
    )
    db.add(intent)


def _close_intent(intent: TransactionIntent) -> dict:
    meta = dict(intent.metadata_json or {})
    terminal = {
        "v3_status": "FAILED",
        "rebalance_execution_id": meta.get("rebalance_execution_id") or BATCH_ID,
        "batch_id": meta.get("batch_id") or BATCH_ID,
        "portfolio_id": str(KINGS_ID),
        "recovery_closed": True,
        "recovery_reason": "orphan_intent_lock_swap",
    }
    sync_bundle_transaction_rebalancing(intent, result=terminal)
    meta.update(terminal)
    intent.metadata_json = meta
    intent.status = "failed"
    return terminal


def main() -> None:
    apply_mode = _apply_mode()
    db = SessionLocal()
    report: dict = {
        "phase": "bundle_v3_orphan_recovery",
        "apply": apply_mode,
        "at": datetime.now(timezone.utc).isoformat(),
        "targets": {
            "person_id": str(PERSON_ID),
            "portfolio_id": str(KINGS_ID),
            "intent_id": str(INTENT_ID),
            "swap_id": str(SWAP_ID),
            "batch_id": BATCH_ID,
        },
    }
    try:
        report["before"] = _snapshot(db)
        actions: list[dict] = []

        if not apply_mode:
            report["actions_planned"] = [
                "terminalize_running_v3_if_present",
                "close_intent_61ba1a78_failed",
                "release_global_user_transaction_lock",
                "expire_swap_a36ac04f_if_not_confirmed",
                "release_active_portfolio_financial_operation",
            ]
            print(json.dumps(report, indent=2, default=str))
            return

        running = find_running_v3_rebalance_execution(db, portfolio_id=str(KINGS_ID))
        if running is not None:
            terminal = force_terminalize_running_v3_rebalance_on_plan_drift(
                db,
                portfolio_id=str(KINGS_ID),
                reason="orphan_recovery",
            )
            if terminal is None:
                from services.portfolio_engine.bundles.rebalance_executor import (
                    terminalize_stale_v3_rebalance_execution,
                )

                terminal = terminalize_stale_v3_rebalance_execution(
                    db, portfolio_id=str(KINGS_ID),
                )
            if terminal is not None:
                _finalize_intent_and_lock(db, terminal=terminal)
                actions.append({"terminalized_v3": terminal.get("v3_status")})

        intent = db.query(TransactionIntent).filter(TransactionIntent.id == INTENT_ID).first()
        if intent is not None and str(intent.status or "").lower() in ("running", "created"):
            terminal = _close_intent(intent)
            _finalize_intent_and_lock(db, terminal=terminal)
            actions.append({"intent_closed": str(intent.id), "v3_status": "FAILED"})

        lock = find_active_global_user_transaction_lock(db, person_id=PERSON_ID)
        if lock is not None:
            released = release_global_user_transaction_lock(
                db, intent_id=lock.intent_id, reason="bundle_v3_orphan_recovery",
            )
            actions.append({"global_lock_released": released.released})

        swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == SWAP_ID).first()
        swap_action = _expire_swap_if_stale(db, swap)
        if swap_action:
            actions.append({"swap": swap_action})

        released_pfo = release_active_bundle_portfolio_operation(
            db, portfolio_id=KINGS_ID, failed=True,
        )
        actions.append({"portfolio_guard_released": released_pfo})

        db.commit()
        report["actions"] = actions
        report["after"] = _snapshot(db)
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
