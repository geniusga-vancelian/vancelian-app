"""Test contrôlé prod B4b — parent FROZEN → bridge → fresh swap → settle → LEDGER_SETTLED.

Modes (env ``BUNDLE_B4B_TEST_MODE``) :
  baseline | create_frozen_parent | run_b4b_bridge | audit | rollback_or_cleanup

Écriture explicite avec ``BUNDLE_B4B_TEST_CONFIRM=1``.
Flags bridge/global lock/B3c activés uniquement dans le process ``run_b4b_bridge``.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    bundle_context_for_swap,
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge import (
    CHILD_STATUS_SWAP_ATTACHED,
    run_bundle_b4b_minimal_bridge,
)
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
)
from services.portfolio_engine.bundles.event_driven.rebalance_planner import compute_plan_hash
from services.product_locks.enums import ProductLockScope
from services.product_locks.global_user_transaction_lock import find_active_global_user_transaction_lock
from services.transaction_intents.bundle_parent_child_repository import find_bundle_leg, find_children

PERSON_ID = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
CLIENT_ID = uuid.UUID("080358a8-4519-4acf-b5da-25485446c967")
WALLET_ID = uuid.UUID("a5bc9936-11f2-411b-be33-f0b63196f65d")

TEST_VERSION = "b4b-minimal-controlled-test-v1"
TEST_KEY_PREFIX = "bundle_b4b_controlled_test"
PLANNER_VERSION = "v1"
MERGE_SHA_B4B = os.environ.get("BUNDLE_B4B_MERGE_SHA", "pending")
MIN_TD_REVISION = int(os.environ.get("BUNDLE_B4B_MIN_TD_REVISION", "157"))

ECON_BASELINE = {"pe": 19, "cb": 67, "lifi_swap_legs": 131}
FROM_ASSET = "USDC"
TO_ASSET = "AAVE"
CHAIN = "base"
HEALTH_URL = os.environ.get("ARQUANTIX_HEALTH_URL", "https://arquantix.com/health")


def _health_ok() -> tuple[bool, int | None, str | None]:
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200, resp.status, None
    except urllib.error.HTTPError as exc:
        return False, exc.code, str(exc)
    except Exception as exc:
        return False, None, str(exc)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confirm_required() -> bool:
    return os.environ.get("BUNDLE_B4B_TEST_CONFIRM", "").strip() in {"1", "true", "yes", "on"}


def _env_uuid(name: str) -> uuid.UUID | None:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    return uuid.UUID(raw)


def _env_decimal(name: str, default: str) -> Decimal:
    return Decimal((os.environ.get(name) or default).strip())


def _flags_snapshot() -> dict[str, Any]:
    keys = (
        "BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED",
        "GLOBAL_USER_TRANSACTION_LOCK_ENABLED",
        "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED",
        "BUNDLE_FUNDING_HANDLER_ENABLED",
        "BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED",
    )
    out: dict[str, Any] = {}
    for key in keys:
        raw = (os.environ.get(key) or "").strip().lower()
        out[key] = raw or None
        out[f"{key}_off"] = raw not in {"1", "true", "yes", "on"}
    return out


def _economic_snapshot(db) -> dict[str, Any]:
    balances = db.execute(
        text(
            """
            SELECT asset, available_balance::text, balance::text
            FROM person_wallet_balances
            WHERE person_id = :pid AND person_crypto_wallet_id = :wid
            ORDER BY asset
            """
        ),
        {"pid": str(PERSON_ID), "wid": str(WALLET_ID)},
    ).fetchall()
    return {
        "pe": db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar(),
        "cb": db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar(),
        "lifi_swap_legs": db.execute(
            text(
                "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
            )
        ).scalar(),
        "active_financial_locks": db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_product_locks
                WHERE scope = :scope AND asset = 'GLOBAL'
                  AND status = 'active' AND released_at IS NULL
                """
            ),
            {"scope": ProductLockScope.FINANCIAL_TRANSACTION.value},
        ).scalar(),
        "dead_letter": db.execute(
            text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")
        ).scalar(),
        "completed": db.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction_intents
                WHERE LOWER(status) = 'completed' OR current_phase = 'COMPLETED'
                """
            )
        ).scalar(),
        "b4b_test_parents": db.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction_intents
                WHERE product_type = 'bundle_invest'
                  AND COALESCE(metadata_json->'b4b_controlled_test'->>'version', '') = :ver
                """
            ),
            {"ver": TEST_VERSION},
        ).scalar(),
        "wallet_balances": {row[0]: {"available": row[1], "balance": row[2]} for row in balances},
    }


def _find_instruments(db) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            SELECT i.id, a.symbol, i.code
            FROM pe_instruments i
            JOIN pe_assets a ON a.id = i.asset_id
            WHERE a.symbol IN ('USDC', 'AAVE') AND i.instrument_type = 'spot'
            ORDER BY a.symbol
            """
        )
    ).fetchall()
    return {str(symbol).upper(): {"instrument_id": str(instr_id), "code": code} for instr_id, symbol, code in rows}


def _resolve_client_id(db) -> uuid.UUID | None:
    row = db.execute(
        text("SELECT id FROM pe_clients WHERE person_id = :pid LIMIT 1"),
        {"pid": str(PERSON_ID)},
    ).fetchone()
    return uuid.UUID(str(row[0])) if row else None


def _find_bundle_portfolios(db, *, client_id: uuid.UUID | None) -> list[dict[str, Any]]:
    if client_id is None:
        return []
    rows = db.execute(
        text(
            """
            SELECT p.id, p.name, p.portfolio_type,
                   COALESCE(p.metadata->>'bundle_code', '') AS bundle_code
            FROM pe_portfolios p
            WHERE p.client_id = :cid
              AND p.portfolio_type = 'bundle_portfolio'
              AND p.status = 'active'
            ORDER BY p.created_at
            """
        ),
        {"cid": str(client_id)},
    ).fetchall()
    return [
        {"portfolio_id": str(r[0]), "name": r[1], "portfolio_type": r[2], "bundle_code": r[3]}
        for r in rows
    ]


def _plan_body_for_test(*, amount_usdc: str) -> dict[str, Any]:
    return {
        "legs": [
            {
                "leg_index": 0,
                "direction": "buy",
                "from_asset": FROM_ASSET,
                "to_asset": TO_ASSET,
                "from_chain": CHAIN,
                "to_chain": CHAIN,
                "notional_usdc": amount_usdc,
            }
        ],
        "skipped": [],
        "residual_usdc": "0",
        "weights_after_funding": {TO_ASSET: 0, FROM_ASSET: 10000},
    }


def _intent_snapshot(db, intent_id: uuid.UUID) -> dict[str, Any] | None:
    row = db.get(TransactionIntent, intent_id)
    if row is None:
        return None
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return {
        "id": str(row.id),
        "product_type": row.product_type,
        "intent_role": row.intent_role,
        "status": row.status,
        "current_phase": row.current_phase,
        "parent_intent_id": str(row.parent_intent_id) if row.parent_intent_id else None,
        "leg_index": row.leg_index,
        "linked_table": row.linked_table,
        "linked_id": str(row.linked_id) if row.linked_id else None,
        "metadata_status": meta.get("status"),
        "plan_hash": meta.get("plan_hash"),
        "bundle_b4b_bridge": meta.get("bundle_b4b_bridge"),
        "bundle_leg_settlement": meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY),
        "metadata_phase": meta.get("phase"),
    }


def _swap_snapshot(db, swap_id: uuid.UUID) -> dict[str, Any] | None:
    swap = db.get(PersonWalletSwap, swap_id)
    if swap is None:
        return None
    ctx = bundle_context_for_swap(swap) or {}
    return {
        "id": str(swap.id),
        "status": swap.status,
        "tx_hash": swap.tx_hash,
        "pair": f"{swap.from_asset}→{swap.to_asset}",
        "chains": f"{swap.from_chain}/{swap.to_chain}",
        "bundle_internal": is_bundle_internal_swap(swap),
        "bundle_leg_context": ctx,
    }


def _enable_bridge_flags_for_job() -> None:
    os.environ["BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED"] = "true"
    os.environ["GLOBAL_USER_TRANSACTION_LOCK_ENABLED"] = "true"
    os.environ["BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED"] = "true"


def mode_baseline(db) -> dict[str, Any]:
    health_ok, health_status, health_error = _health_ok()
    econ = _economic_snapshot(db)
    flags = _flags_snapshot()
    instruments = _find_instruments(db)
    client_id = _resolve_client_id(db)
    portfolios = _find_bundle_portfolios(db, client_id=client_id)
    portfolio_id = (os.environ.get("PORTFOLIO_ID") or "").strip() or None
    if not portfolio_id and len(portfolios) == 1:
        portfolio_id = portfolios[0]["portfolio_id"]
    usdc_avail = (econ.get("wallet_balances") or {}).get("USDC", {}).get("available")
    checks = {
        "flags_b4b_off": flags["BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED_off"],
        "flags_global_lock_off": flags["GLOBAL_USER_TRANSACTION_LOCK_ENABLED_off"],
        "flags_b3c_off": flags["BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED_off"],
        "pe_baseline": econ["pe"] == ECON_BASELINE["pe"],
        "cb_baseline": econ["cb"] == ECON_BASELINE["cb"],
        "legs_baseline": econ["lifi_swap_legs"] == ECON_BASELINE["lifi_swap_legs"],
        "active_financial_locks_zero": econ["active_financial_locks"] == 0,
        "dead_letter_zero": econ["dead_letter"] == 0,
        "completed_zero": econ["completed"] == 0,
        "instruments_usdc_aave": "USDC" in instruments and "AAVE" in instruments,
        "portfolio_found": portfolio_id is not None,
        "health_ok": health_ok,
        "usdc_wallet_available": usdc_avail is not None and Decimal(str(usdc_avail)) > 0,
    }
    return {
        "phase": "bundle_b4b_minimal_controlled_test",
        "mode": "baseline",
        "baseline_ok": all(checks.values()),
        "health": {"url": HEALTH_URL, "ok": health_ok, "status": health_status, "error": health_error},
        "merge_sha_b4b": MERGE_SHA_B4B,
        "min_td_revision": MIN_TD_REVISION,
        "person_id": str(PERSON_ID),
        "client_id": str(client_id) if client_id else None,
        "wallet_id": str(WALLET_ID),
        "flags": flags,
        "economic": econ,
        "economic_baseline": ECON_BASELINE,
        "instruments": instruments,
        "bundle_portfolios": portfolios,
        "selected_portfolio_id": portfolio_id,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "next_step": "create_frozen_parent avec CONFIRM=1 PORTFOLIO_ID=... AMOUNT_USDC=1",
    }


def mode_create_frozen_parent(db) -> dict[str, Any]:
    if not _confirm_required():
        raise RuntimeError("create_frozen_parent_requires_BUNDLE_B4B_TEST_CONFIRM=1")

    amount = _env_decimal("AMOUNT_USDC", "1")
    portfolio_id_raw = (os.environ.get("PORTFOLIO_ID") or "").strip()
    if not portfolio_id_raw:
        client_id = _resolve_client_id(db)
        portfolios = _find_bundle_portfolios(db, client_id=client_id)
        if len(portfolios) == 1:
            portfolio_id_raw = portfolios[0]["portfolio_id"]
        else:
            raise RuntimeError(f"PORTFOLIO_ID_required:found={len(portfolios)} bundle_portfolios")

    run_id = (os.environ.get("TEST_RUN_ID") or "").strip() or uuid.uuid4().hex
    plan_body = _plan_body_for_test(amount_usdc=str(amount))
    plan_hash = compute_plan_hash(plan_body)
    bundle_execution_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    from services.transaction_intents.enums import (
        IntentOperationType,
        IntentProductType,
        IntentRole,
        IntentStatus,
    )

    parent = TransactionIntent(
        id=parent_id,
        person_id=PERSON_ID,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        operation_type=IntentOperationType.INVEST.value,
        idempotency_key=f"{TEST_KEY_PREFIX}:parent:{run_id}",
        status=IntentStatus.CREATED.value,
        intent_role=IntentRole.PARENT.value,
        bundle_execution_id=bundle_execution_id,
        linked_table="bundle_invest_lock",
        linked_reference_id=str(bundle_execution_id),
        metadata_json={
            "phase": "REBALANCE_PLAN_FROZEN",
            "planner_version": PLANNER_VERSION,
            "plan_hash": plan_hash,
            "rebalance_plan_after_funding": plan_body,
            "portfolio_id": portfolio_id_raw,
            "funding_usdc": str(amount),
            "b4b_controlled_test": {
                "version": TEST_VERSION,
                "run_id": run_id,
                "status": "parent_frozen",
                "created_at": _utc_now_iso(),
            },
        },
    )
    db.add(parent)
    db.commit()

    children = find_children(db, parent_intent_id=parent_id)
    if children:
        raise RuntimeError("create_frozen_parent_must_not_create_child")

    return {
        "phase": "bundle_b4b_minimal_controlled_test",
        "mode": "create_frozen_parent",
        "test_run_id": run_id,
        "plan_hash": plan_hash,
        "parent_intent_id": str(parent_id),
        "portfolio_id": portfolio_id_raw,
        "amount_usdc": str(amount),
        "child_count": 0,
        "parent_snapshot": _intent_snapshot(db, parent_id),
        "next_step": f"run_b4b_bridge CONFIRM=1 PARENT_INTENT_ID={parent_id}",
    }


def mode_run_b4b_bridge(db) -> dict[str, Any]:
    if not _confirm_required():
        raise RuntimeError("run_b4b_bridge_requires_BUNDLE_B4B_TEST_CONFIRM=1")

    parent_id = _env_uuid("PARENT_INTENT_ID")
    if parent_id is None:
        raise RuntimeError("PARENT_INTENT_ID_required")

    econ_before = _economic_snapshot(db)
    _enable_bridge_flags_for_job()

    bridge_result = run_bundle_b4b_minimal_bridge(db, parent_intent_id=parent_id)
    db.commit()

    child = find_bundle_leg(db, parent_intent_id=parent_id, leg_index=0)
    swap_id = bridge_result.swap_id or (child.linked_id if child else None)
    swap_snap = _swap_snapshot(db, swap_id) if swap_id else None
    active_lock = find_active_global_user_transaction_lock(db, person_id=PERSON_ID)
    econ_after = _economic_snapshot(db)

    settlement = None
    if child is not None:
        meta = child.metadata_json if isinstance(child.metadata_json, dict) else {}
        settlement = meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY)

    ctx = (swap_snap or {}).get("bundle_leg_context") or {}
    checks = {
        "child_created_or_reused": child is not None,
        "exactly_one_child": len(find_children(db, parent_intent_id=parent_id)) == 1,
        "fresh_swap_linked": swap_id is not None and child is not None and child.linked_id == swap_id,
        "swap_bundle_internal": (swap_snap or {}).get("bundle_internal") is True,
        "swap_context_has_plan_hash": bool(ctx.get("plan_hash")),
        "swap_context_has_planner_version": bool(ctx.get("planner_version")),
        "child_swap_attached_or_settled": (
            (child.metadata_json or {}).get("status") in {CHILD_STATUS_SWAP_ATTACHED, "awaiting_swap"}
            or (settlement or {}).get("phase") == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED
        ),
        "ledger_settled_if_confirmed": (
            not bridge_result.settled
            or (settlement or {}).get("phase") == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED
        ),
        "lock_released_if_settled": (
            not bridge_result.settled or active_lock is None
        ),
        "no_settlement_if_awaiting_confirmation": (
            not bridge_result.awaiting_swap_confirmation
            or settlement is None
        ),
    }

    return {
        "phase": "bundle_b4b_minimal_controlled_test",
        "mode": "run_b4b_bridge",
        "parent_intent_id": str(parent_id),
        "bridge_result": {
            "skipped": bridge_result.skipped,
            "idempotent": bridge_result.idempotent,
            "completed": bridge_result.completed,
            "settled": bridge_result.settled,
            "child_intent_id": str(bridge_result.child_intent_id) if bridge_result.child_intent_id else None,
            "swap_id": str(bridge_result.swap_id) if bridge_result.swap_id else None,
            "global_lock_acquired": bridge_result.global_lock_acquired,
            "global_lock_released": bridge_result.global_lock_released,
            "awaiting_swap_confirmation": bridge_result.awaiting_swap_confirmation,
            "reason": bridge_result.reason,
        },
        "child_snapshot": _intent_snapshot(db, child.id) if child else None,
        "swap_snapshot": swap_snap,
        "active_financial_lock": str(active_lock.intent_id) if active_lock else None,
        "economic_before": econ_before,
        "economic_after": econ_after,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "next_step": (
            "run_b4b_bridge REPEAT après CONFIRMED on-chain"
            if bridge_result.awaiting_swap_confirmation
            else "audit puis run_b4b_bridge REPEAT idempotence"
        ),
    }


def mode_audit(db) -> dict[str, Any]:
    parent_id = _env_uuid("PARENT_INTENT_ID")
    if parent_id is None:
        raise RuntimeError("PARENT_INTENT_ID_required")

    parent = db.get(TransactionIntent, parent_id)
    child = find_bundle_leg(db, parent_intent_id=parent_id, leg_index=0)
    swap_snap = _swap_snapshot(db, child.linked_id) if child and child.linked_id else None
    econ = _economic_snapshot(db)
    active_lock = find_active_global_user_transaction_lock(db, person_id=PERSON_ID)

    parent_meta = parent.metadata_json if parent and isinstance(parent.metadata_json, dict) else {}
    child_meta = child.metadata_json if child and isinstance(child.metadata_json, dict) else {}
    settlement = child_meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY) or {}

    checks = {
        "parent_not_completed": parent_meta.get("phase") not in {"COMPLETED", "RECONCILED"},
        "child_ledger_settled": settlement.get("phase") == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
        "settlement_receipt_present": bool(child_meta.get("settlement_receipt_hash")),
        "child_report_present": bool(child_meta.get("child_report_hash")),
        "active_financial_locks_zero": econ["active_financial_locks"] == 0,
        "dead_letter_zero": econ["dead_letter"] == 0,
        "completed_zero": econ["completed"] == 0,
        "swap_confirmed_if_settled": (
            settlement.get("phase") != BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED
            or (swap_snap or {}).get("status", "").upper() == SwapSessionStatus.CONFIRMED.value
        ),
    }

    return {
        "phase": "bundle_b4b_minimal_controlled_test",
        "mode": "audit",
        "parent_intent_id": str(parent_id),
        "child_intent_id": str(child.id) if child else None,
        "swap_id": str(child.linked_id) if child and child.linked_id else None,
        "parent_snapshot": _intent_snapshot(db, parent_id),
        "child_snapshot": _intent_snapshot(db, child.id) if child else None,
        "swap_snapshot": swap_snap,
        "active_financial_lock": str(active_lock.intent_id) if active_lock else None,
        "economic": econ,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }


def mode_rollback_or_cleanup(db) -> dict[str, Any]:
    if not _confirm_required():
        raise RuntimeError("rollback_or_cleanup_requires_BUNDLE_B4B_TEST_CONFIRM=1")

    parent_id = _env_uuid("PARENT_INTENT_ID")
    child = find_bundle_leg(db, parent_intent_id=parent_id, leg_index=0) if parent_id else None
    if parent_id is None or child is None:
        raise RuntimeError("PARENT_INTENT_ID_with_child_required")

    meta = child.metadata_json if isinstance(child.metadata_json, dict) else {}
    settlement = meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY)
    if isinstance(settlement, dict) and settlement.get("settled") is True:
        raise RuntimeError("refuse_cleanup_after_ledger_settled")

    from services.product_locks.global_user_transaction_lock import release_global_user_transaction_lock
    from services.transaction_intents.enums import IntentStatus

    release_global_user_transaction_lock(db, intent_id=parent_id, reason="b4b_test_cleanup")
    child.status = IntentStatus.FAILED.value
    test_block = dict(meta.get("b4b_controlled_test") or {})
    test_block["status"] = "cleanup_failed"
    test_block["cleanup_at"] = _utc_now_iso()
    meta["b4b_controlled_test"] = test_block
    child.metadata_json = meta
    db.add(child)

    parent = db.get(TransactionIntent, parent_id)
    if parent is not None:
        parent.status = IntentStatus.FAILED.value
        parent_meta = parent.metadata_json if isinstance(parent.metadata_json, dict) else {}
        test_block_p = dict(parent_meta.get("b4b_controlled_test") or {})
        test_block_p["status"] = "cleanup_failed"
        test_block_p["cleanup_at"] = _utc_now_iso()
        parent_meta["b4b_controlled_test"] = test_block_p
        parent.metadata_json = parent_meta
        db.add(parent)

    if child.linked_table == "person_wallet_swaps":
        child.linked_table = None
        child.linked_id = None
        db.add(child)

    db.commit()
    return {
        "phase": "bundle_b4b_minimal_controlled_test",
        "mode": "rollback_or_cleanup",
        "parent_intent_id": str(parent_id),
        "child_intent_id": str(child.id),
        "action": "released_lock_marked_failed_unlinked_swap",
    }


def main() -> None:
    mode = (os.environ.get("BUNDLE_B4B_TEST_MODE") or "").strip().lower()
    handlers = {
        "baseline": mode_baseline,
        "create_frozen_parent": mode_create_frozen_parent,
        "run_b4b_bridge": mode_run_b4b_bridge,
        "audit": mode_audit,
        "rollback_or_cleanup": mode_rollback_or_cleanup,
    }
    if mode not in handlers:
        raise RuntimeError(f"invalid_mode:{mode!r} — expected one of {sorted(handlers)}")

    db = SessionLocal()
    try:
        result = handlers[mode](db)
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
