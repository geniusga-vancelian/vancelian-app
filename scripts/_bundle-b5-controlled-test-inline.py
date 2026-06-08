"""Test contrôlé prod B5 — parent proof aggregator → RECONCILED.

Modes (env ``BUNDLE_B5_TEST_MODE``) :
  baseline | reconcile_parent | audit

Parent cible par défaut : B4b controlled test ``0ef6517e-10c1-453b-bce7-3e6ff08c866d``.
Flag ``BUNDLE_PARENT_CONTROLLER_ENABLED`` activé uniquement dans le job ``reconcile_parent``.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from database import SessionLocal
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
)
from services.portfolio_engine.bundles.event_driven.bundle_parent_controller import (
    PHASE_RECONCILED,
    reconcile_bundle_parent_idempotently,
)
from services.product_locks.enums import ProductLockScope
from services.transaction_intents.bundle_parent_child_repository import find_children
from services.transaction_intents.enums import IntentProductType, IntentRole

PERSON_ID = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
DEFAULT_PARENT_ID = uuid.UUID("0ef6517e-10c1-453b-bce7-3e6ff08c866d")
ECON_BASELINE = {"pe": 19, "cb": 67, "lifi_swap_legs": 131}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confirm_required() -> bool:
    return os.environ.get("BUNDLE_B5_TEST_CONFIRM", "").strip() in {"1", "true", "yes", "on"}


def _env_parent_id() -> uuid.UUID:
    raw = (os.environ.get("PARENT_INTENT_ID") or "").strip()
    return uuid.UUID(raw) if raw else DEFAULT_PARENT_ID


def _economic_snapshot(db) -> dict[str, int]:
    pe = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
    cb = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    legs = db.execute(
        text(
            "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
        )
    ).scalar()
    locks = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM transaction_product_locks
            WHERE scope = :scope AND asset = 'GLOBAL' AND status = 'active' AND released_at IS NULL
            """
        ),
        {"scope": ProductLockScope.FINANCIAL_TRANSACTION.value},
    ).scalar()
    dead_letter = db.execute(
        text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")
    ).scalar()
    completed = db.execute(
        text(
            """
            SELECT COUNT(*) FROM transaction_intents
            WHERE metadata_json->>'phase' = 'COMPLETED' OR current_phase = 'COMPLETED'
            """
        )
    ).scalar()
    return {
        "pe": int(pe),
        "cb": int(cb),
        "lifi_swap_legs": int(legs),
        "active_financial_locks": int(locks),
        "dead_letter": int(dead_letter),
        "completed": int(completed),
    }


def _intent_snapshot(row: TransactionIntent | None) -> dict[str, Any] | None:
    if row is None:
        return None
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return {
        "id": str(row.id),
        "product_type": row.product_type,
        "intent_role": row.intent_role,
        "status": row.status,
        "current_phase": row.current_phase,
        "metadata_phase": meta.get("phase"),
        "parent_report_hash": meta.get("parent_report_hash"),
        "bundle_parent_controller": meta.get("bundle_parent_controller"),
        "bundle_leg_settlement": meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY),
    }


def _mode_baseline(db) -> dict[str, Any]:
    flags = {
        "BUNDLE_PARENT_CONTROLLER_ENABLED": os.environ.get("BUNDLE_PARENT_CONTROLLER_ENABLED"),
    }
    economic = _economic_snapshot(db)
    checks = {
        "flag_b5_off": not (os.environ.get("BUNDLE_PARENT_CONTROLLER_ENABLED") or "").strip(),
        "pe_baseline": economic["pe"] == ECON_BASELINE["pe"],
        "cb_baseline": economic["cb"] == ECON_BASELINE["cb"],
        "legs_baseline": economic["lifi_swap_legs"] == ECON_BASELINE["lifi_swap_legs"],
        "completed_zero": economic["completed"] == 0,
    }
    return {
        "phase": "bundle_b5_controlled_test",
        "mode": "baseline",
        "flags": flags,
        "economic": economic,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "next_step": "reconcile_parent avec CONFIRM=1 PARENT_INTENT_ID=0ef6517e...",
    }


def _mode_reconcile_parent(db) -> dict[str, Any]:
    if not _confirm_required():
        raise SystemExit("BUNDLE_B5_TEST_CONFIRM=1 requis pour reconcile_parent")
    os.environ["BUNDLE_PARENT_CONTROLLER_ENABLED"] = "true"

    parent_id = _env_parent_id()
    economic_before = _economic_snapshot(db)
    parent_before = db.get(TransactionIntent, parent_id)
    children_before = find_children(db, parent_intent_id=parent_id)
    child_meta_before = [
        dict(c.metadata_json or {}) if isinstance(c.metadata_json, dict) else {}
        for c in children_before
    ]

    result = reconcile_bundle_parent_idempotently(db, parent_intent_id=parent_id)
    db.commit()

    parent_after = db.get(TransactionIntent, parent_id)
    children_after = find_children(db, parent_intent_id=parent_id)
    economic_after = _economic_snapshot(db)

    child_unchanged = all(
        (after.metadata_json if isinstance(after.metadata_json, dict) else {})
        == before
        for after, before in zip(children_after, child_meta_before)
    )

    checks = {
        "reconciled": result.reconciled,
        "parent_report_hash_present": bool(result.parent_report_hash),
        "parent_phase_reconciled": (parent_after.metadata_json or {}).get("phase") == PHASE_RECONCILED,
        "child_metadata_unchanged": child_unchanged,
        "pe_unchanged": economic_before["pe"] == economic_after["pe"],
        "cb_unchanged": economic_before["cb"] == economic_after["cb"],
        "legs_unchanged": economic_before["lifi_swap_legs"] == economic_after["lifi_swap_legs"],
        "completed_zero": economic_after["completed"] == 0,
        "no_completed_parent": (parent_after.metadata_json or {}).get("phase") != "COMPLETED",
    }

    return {
        "phase": "bundle_b5_controlled_test",
        "mode": "reconcile_parent",
        "parent_intent_id": str(parent_id),
        "reconcile_result": {
            "skipped": result.skipped,
            "idempotent": result.idempotent,
            "reconciled": result.reconciled,
            "parent_report_hash": result.parent_report_hash,
            "plan_hash": result.plan_hash,
            "child_report_hashes": list(result.child_report_hashes),
            "reason": result.reason,
        },
        "parent_snapshot": _intent_snapshot(parent_after),
        "child_snapshots": [_intent_snapshot(c) for c in children_after],
        "economic_before": economic_before,
        "economic_after": economic_after,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "next_step": "audit puis reconcile_parent REPEAT idempotence",
    }


def _mode_audit(db) -> dict[str, Any]:
    parent_id = _env_parent_id()
    parent = db.get(TransactionIntent, parent_id)
    children = find_children(db, parent_intent_id=parent_id)
    economic = _economic_snapshot(db)
    meta = parent.metadata_json if isinstance(parent.metadata_json, dict) else {}

    all_children_settled = all(
        isinstance((c.metadata_json or {}).get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY), dict)
        and (c.metadata_json or {}).get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY, {}).get("phase")
        == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED
        for c in children
    )

    checks = {
        "parent_reconciled": meta.get("phase") == PHASE_RECONCILED,
        "parent_report_hash_present": bool(meta.get("parent_report_hash")),
        "bundle_parent_controller_block": isinstance(meta.get("bundle_parent_controller"), dict),
        "all_children_ledger_settled": all_children_settled,
        "parent_not_completed": meta.get("phase") != "COMPLETED",
        "pe_baseline": economic["pe"] == ECON_BASELINE["pe"],
        "cb_baseline": economic["cb"] == ECON_BASELINE["cb"],
        "legs_baseline": economic["lifi_swap_legs"] == ECON_BASELINE["lifi_swap_legs"],
        "completed_zero": economic["completed"] == 0,
    }

    return {
        "phase": "bundle_b5_controlled_test",
        "mode": "audit",
        "parent_intent_id": str(parent_id),
        "parent_snapshot": _intent_snapshot(parent),
        "child_snapshots": [_intent_snapshot(c) for c in children],
        "economic": economic,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }


def main() -> None:
    mode = (os.environ.get("BUNDLE_B5_TEST_MODE") or "").strip().lower()
    db = SessionLocal()
    try:
        if mode == "baseline":
            out = _mode_baseline(db)
        elif mode == "reconcile_parent":
            out = _mode_reconcile_parent(db)
        elif mode == "audit":
            out = _mode_audit(db)
        else:
            raise SystemExit(f"Mode inconnu: {mode!r}")
        print(json.dumps(out, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
