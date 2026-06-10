"""Debug active-operation Kings/Majors — pourquoi status=active."""
from __future__ import annotations

import json
from uuid import UUID

from database import SessionLocal
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_invest_lock import (
    find_active_bundle_batch_ids_for_portfolio,
    get_active_invest_lock_for_portfolio,
    peek_bundle_invest_lock_state,
)
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    find_running_bundle_transaction_intent_for_portfolio,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
    is_v3_deposit_batch,
)
from services.portfolio_engine.bundles.rebalance_executor import (
    find_running_v3_rebalance_execution,
)
from services.portfolio_engine.bundles.rebalancing_portfolio import (
    get_active_bundle_operation,
    reconcile_stale_bundle_portfolio_state,
)

CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
PERSON_ID = UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
KINGS_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")
MAJORS_ID = UUID("ab4ae920-f3e8-481b-8f82-a41a81d5779d")


def _intents_for_portfolio(db, portfolio_id: UUID) -> list[dict]:
    pid = str(portfolio_id)
    rows = (
        db.query(TransactionIntent)
        .filter(TransactionIntent.person_id == PERSON_ID)
        .order_by(TransactionIntent.created_at.desc())
        .limit(40)
        .all()
    )
    out: list[dict] = []
    for row in rows:
        meta = row.metadata_json or {}
        if str(meta.get("portfolio_id") or meta.get("bundle_id") or "") != pid:
            continue
        out.append({
            "id": str(row.id),
            "product_type": row.product_type,
            "status": row.status,
            "created_at": str(row.created_at),
            "v3_status": meta.get("v3_status"),
            "batch_id": meta.get("batch_id"),
            "legs": meta.get("legs"),
        })
    return out


def _debug_portfolio(db, portfolio_id: UUID, name: str) -> dict:
    active = get_active_bundle_operation(db, client_id=CLIENT_ID, portfolio_id=portfolio_id)
    running = find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio_id))
    orphan = find_running_bundle_transaction_intent_for_portfolio(db, portfolio_id=portfolio_id)
    lock = get_active_invest_lock_for_portfolio(db, client_id=CLIENT_ID, portfolio_id=portfolio_id)
    peek = peek_bundle_invest_lock_state(db, client_id=CLIENT_ID, portfolio_id=portfolio_id)
    batches = find_active_bundle_batch_ids_for_portfolio(
        db, client_id=CLIENT_ID, portfolio_id=portfolio_id,
    )
    v3_lock_active = False
    if lock is not None:
        bid = str(lock.get("batch_id") or "")
        v3_lock_active = bool(
            bid and is_v3_deposit_batch(db, portfolio_id=portfolio_id, batch_id=bid),
        )
    return {
        "name": name,
        "portfolio_id": str(portfolio_id),
        "active_operation": active,
        "running_v3": running,
        "orphan_bundle_transaction_intent": (
            {
                "id": str(orphan.id),
                "status": orphan.status,
                "v3_status": (orphan.metadata_json or {}).get("v3_status"),
            }
            if orphan is not None
            else None
        ),
        "metadata_invest_lock": lock,
        "peek_lock": peek,
        "pending_allocation_batches": batches,
        "v3_deposit_lock_would_show_active": v3_lock_active,
        "intents": _intents_for_portfolio(db, portfolio_id),
    }


def main() -> None:
    db = SessionLocal()
    try:
        report = {
            "before": {
                "kings": _debug_portfolio(db, KINGS_ID, "Kings"),
                "majors": _debug_portfolio(db, MAJORS_ID, "Majors"),
            },
        }
        reconcile_kings = reconcile_stale_bundle_portfolio_state(
            db, client_id=CLIENT_ID, portfolio_id=KINGS_ID,
        )
        reconcile_majors = reconcile_stale_bundle_portfolio_state(
            db, client_id=CLIENT_ID, portfolio_id=MAJORS_ID,
        )
        db.commit()
        report["reconcile_kings"] = reconcile_kings
        report["reconcile_majors"] = reconcile_majors
        report["after"] = {
            "kings": _debug_portfolio(db, KINGS_ID, "Kings"),
            "majors": _debug_portfolio(db, MAJORS_ID, "Majors"),
        }
        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
