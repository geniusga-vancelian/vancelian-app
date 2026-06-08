"""Test contrôlé prod B3c — 1 parent · 1 child · 1 buy leg USDC→AAVE Base.

Modes (env ``BUNDLE_B3C_TEST_MODE``) :
  baseline | setup_parent_child | attach_existing_swap | settle_child | audit | rollback_or_cleanup

Écriture explicite uniquement avec ``BUNDLE_B3C_TEST_CONFIRM=1``.
Le flag handler n'est activé que dans le process du job ``settle_child`` (pas la TD ECS).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    bundle_context_for_swap,
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
    settle_bundle_leg_idempotently,
)
from services.portfolio_engine.bundles.event_driven.rebalance_planner import compute_plan_hash
from services.transaction_intents.bundle_parent_child_repository import bundle_child_idempotency_key
from services.transaction_intents.enums import (
    IntentOperationType,
    IntentProductType,
    IntentRole,
    IntentStatus,
)

# Compte pilote prod (aligné GO_S4 / GO_PILOT)
PERSON_ID = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
CLIENT_ID = uuid.UUID("080358a8-4519-4acf-b5da-25485446c967")
WALLET_ID = uuid.UUID("a5bc9936-11f2-411b-be33-f0b63196f65d")
WALLET_ADDRESS = "0x7ae683c429ec2bc66bf1eb93713b5644dd265a44"

TEST_VERSION = "b3c-controlled-test-v1"
TEST_KEY_PREFIX = "bundle_b3c_controlled_test"
PLANNER_VERSION = "v1"
MERGE_SHA_B3C = "660b1964"
MIN_TD_REVISION = 154

ECON_BASELINE = {"pe": 19, "cb": 67, "lifi_swap_legs": 131}
FROM_ASSET = "USDC"
TO_ASSET = "AAVE"
CHAIN = "base"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confirm_required() -> bool:
    return os.environ.get("BUNDLE_B3C_TEST_CONFIRM", "").strip() in {"1", "true", "yes", "on"}


def _env_uuid(name: str) -> uuid.UUID | None:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    return uuid.UUID(raw)


def _env_decimal(name: str, default: str) -> Decimal:
    raw = (os.environ.get(name) or default).strip()
    return Decimal(raw)


def _flags_snapshot() -> dict[str, Any]:
    funding = (os.environ.get("BUNDLE_FUNDING_HANDLER_ENABLED") or "").strip().lower()
    leg = (os.environ.get("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED") or "").strip().lower()
    dual = (os.environ.get("BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED") or "").strip().lower()
    return {
        "BUNDLE_FUNDING_HANDLER_ENABLED": funding or None,
        "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED": leg or None,
        "BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED": dual or None,
        "funding_off": funding not in {"1", "true", "yes", "on"},
        "leg_off": leg not in {"1", "true", "yes", "on"},
        "dual_off": dual not in {"1", "true", "yes", "on"},
    }


def _economic_snapshot(db) -> dict[str, Any]:
    balances = db.execute(
        text(
            """
            SELECT asset, available_balance::text, balance::text
            FROM person_wallet_balances
            WHERE person_id = :pid AND wallet_id = :wid
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
        "active_locks": db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_product_locks
                WHERE status = 'active' AND released_at IS NULL
                """
            )
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
        "bundle_test_children": db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE product_type = 'bundle_leg'
                  AND intent_role = 'child'
                  AND (
                    idempotency_key LIKE :pfx
                    OR COALESCE(metadata_json->'b3c_controlled_test'->>'version', '') = :ver
                  )
                """
            ),
            {"pfx": f"{TEST_KEY_PREFIX}:%", "ver": TEST_VERSION},
        ).scalar(),
        "wallet_balances": {
            row[0]: {"available": row[1], "balance": row[2]} for row in balances
        },
    }


def _find_instruments(db) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            SELECT i.id, a.symbol, i.code
            FROM pe_instruments i
            JOIN pe_assets a ON a.id = i.asset_id
            WHERE a.symbol IN ('USDC', 'AAVE')
              AND i.instrument_type = 'spot'
            ORDER BY a.symbol
            """
        )
    ).fetchall()
    out: dict[str, str] = {}
    for instr_id, symbol, code in rows:
        out[str(symbol).upper()] = {"instrument_id": str(instr_id), "code": code}
    return out


def _find_bundle_portfolios(db) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT p.id, p.name, p.product_type,
                   COALESCE(p.metadata_json->>'bundle_code', '') AS bundle_code
            FROM pe_portfolios p
            WHERE p.client_id = :cid
              AND p.product_type = 'crypto_bundle'
            ORDER BY p.created_at
            """
        ),
        {"cid": str(CLIENT_ID)},
    ).fetchall()
    return [
        {
            "portfolio_id": str(r[0]),
            "name": r[1],
            "product_type": r[2],
            "bundle_code": r[3],
        }
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
                "amount_in_usdc": amount_usdc,
            }
        ],
        "skipped": [],
        "residual_usdc": "0",
        "weights_after_funding": {TO_ASSET: 0, FROM_ASSET: 10000},
    }


def _candidate_swaps(db, *, portfolio_id: str | None, limit: int = 10) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT s.id, s.status, s.from_asset, s.to_asset, s.from_chain, s.to_chain,
                   s.tx_hash, s.amount_in::text,
                   EXISTS (
                     SELECT 1 FROM transaction_intents ti
                     WHERE ti.linked_table = 'person_wallet_swaps'
                       AND ti.linked_id = s.id
                   ) AS linked_to_intent
            FROM person_wallet_swaps s
            WHERE s.person_id = :pid
              AND UPPER(s.from_asset) = :from_a
              AND UPPER(s.to_asset) = :to_a
              AND LOWER(COALESCE(s.from_chain, '')) = :chain
              AND LOWER(COALESCE(s.to_chain, '')) = :chain
              AND UPPER(COALESCE(s.status, '')) = 'CONFIRMED'
              AND COALESCE(s.tx_hash, '') <> ''
            ORDER BY s.confirmed_at DESC NULLS LAST, s.created_at DESC
            LIMIT :lim
            """
        ),
        {
            "pid": str(PERSON_ID),
            "from_a": FROM_ASSET,
            "to_a": TO_ASSET,
            "chain": CHAIN,
            "lim": limit,
        },
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        swap = db.get(PersonWalletSwap, row[0])
        ctx = bundle_context_for_swap(swap) if swap else None
        out.append(
            {
                "swap_id": str(row[0]),
                "status": row[1],
                "pair": f"{row[2]}→{row[3]}",
                "chains": f"{row[4]}/{row[5]}",
                "tx_hash": row[6],
                "amount_in": row[7],
                "linked_to_intent": bool(row[8]),
                "bundle_internal": is_bundle_internal_swap(swap) if swap else False,
                "bundle_execution": bool((ctx or {}).get("bundle_execution")),
                "portfolio_id_in_audit": (ctx or {}).get("portfolio_id"),
                "portfolio_match": (
                    portfolio_id is None
                    or str((ctx or {}).get("portfolio_id") or "") == portfolio_id
                ),
                "swap_settlement_applied": swap_settlement_already_applied(swap) if swap else None,
            }
        )
    return out


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
        "plan_hash": meta.get("plan_hash"),
        "settlement_receipt_hash": meta.get("settlement_receipt_hash"),
        "child_report_hash": meta.get("child_report_hash"),
        "bundle_leg_settlement": meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY),
        "metadata_phase": meta.get("phase"),
        "metadata_json": meta,
    }


def _baseline_checks(econ: dict[str, Any], flags: dict[str, Any]) -> dict[str, bool]:
    return {
        "flags_all_off": flags["funding_off"] and flags["leg_off"] and flags["dual_off"],
        "pe_baseline": econ["pe"] == ECON_BASELINE["pe"],
        "cb_baseline": econ["cb"] == ECON_BASELINE["cb"],
        "legs_baseline": econ["lifi_swap_legs"] == ECON_BASELINE["lifi_swap_legs"],
        "active_locks_zero": econ["active_locks"] == 0,
        "dead_letter_zero": econ["dead_letter"] == 0,
        "completed_zero": econ["completed"] == 0,
        "no_prior_test_children": econ["bundle_test_children"] == 0,
    }


def mode_baseline(db) -> dict[str, Any]:
    econ = _economic_snapshot(db)
    flags = _flags_snapshot()
    instruments = _find_instruments(db)
    portfolios = _find_bundle_portfolios(db)
    portfolio_id = (
        os.environ.get("PORTFOLIO_ID", "").strip()
        or (portfolios[0]["portfolio_id"] if len(portfolios) == 1 else None)
    )
    usdc_avail = (econ.get("wallet_balances") or {}).get("USDC", {}).get("available")
    checks = _baseline_checks(econ, flags)
    candidates = _candidate_swaps(db, portfolio_id=portfolio_id)
    attach_ready = [
        c
        for c in candidates
        if not c["linked_to_intent"]
        and c["bundle_internal"]
        and c["portfolio_match"]
    ]
    checks["usdc_wallet_available"] = usdc_avail is not None and Decimal(str(usdc_avail)) > 0
    checks["instruments_usdc_aave"] = "USDC" in instruments and "AAVE" in instruments
    checks["portfolio_found"] = portfolio_id is not None
    checks["attach_candidate_exists"] = len(attach_ready) > 0
    return {
        "phase": "bundle_b3c_controlled_test",
        "mode": "baseline",
        "merge_sha_b3c": MERGE_SHA_B3C,
        "min_td_revision": MIN_TD_REVISION,
        "deploy_git_sha": os.environ.get("GIT_SHA") or os.environ.get("GIT_COMMIT"),
        "person_id": str(PERSON_ID),
        "client_id": str(CLIENT_ID),
        "wallet_id": str(WALLET_ID),
        "flags": flags,
        "economic": econ,
        "economic_baseline": ECON_BASELINE,
        "instruments": instruments,
        "bundle_portfolios": portfolios,
        "selected_portfolio_id": portfolio_id,
        "usdc_available": usdc_avail,
        "candidate_swaps": candidates,
        "attach_ready_swaps": attach_ready,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "next_step": (
            "setup_parent_child avec CONFIRM=1 PORTFOLIO_ID=... AMOUNT_USDC=1"
            if checks["portfolio_found"]
            else "définir PORTFOLIO_ID explicitement"
        ),
    }


def mode_setup_parent_child(db) -> dict[str, Any]:
    if not _confirm_required():
        raise RuntimeError("setup_parent_child_requires_BUNDLE_B3C_TEST_CONFIRM=1")

    amount = _env_decimal("AMOUNT_USDC", "1")
    portfolio_id_raw = (os.environ.get("PORTFOLIO_ID") or "").strip()
    if not portfolio_id_raw:
        portfolios = _find_bundle_portfolios(db)
        if len(portfolios) != 1:
            raise RuntimeError(
                f"PORTFOLIO_ID_required:found={len(portfolios)} portfolios"
            )
        portfolio_id_raw = portfolios[0]["portfolio_id"]

    instruments = _find_instruments(db)
    if "USDC" not in instruments or "AAVE" not in instruments:
        raise RuntimeError("missing_usdc_or_aave_instruments")

    run_id = (os.environ.get("TEST_RUN_ID") or "").strip() or uuid.uuid4().hex
    plan_body = _plan_body_for_test(amount_usdc=str(amount))
    plan_hash = compute_plan_hash(plan_body)

    bundle_execution_id = uuid.uuid4()
    parent_id = uuid.uuid4()
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
            "b3c_controlled_test": {
                "version": TEST_VERSION,
                "run_id": run_id,
                "status": "setup",
                "created_at": _utc_now_iso(),
            },
        },
    )
    db.add(parent)
    db.flush()

    child = TransactionIntent(
        person_id=PERSON_ID,
        product_type=IntentProductType.BUNDLE_LEG.value,
        operation_type=IntentOperationType.BUNDLE_LEG.value,
        idempotency_key=bundle_child_idempotency_key(parent_intent_id=parent_id, leg_index=0),
        status=IntentStatus.SUBMITTED.value,
        intent_role=IntentRole.CHILD.value,
        parent_intent_id=parent_id,
        leg_index=0,
        bundle_execution_id=bundle_execution_id,
        metadata_json={
            "plan_hash": plan_hash,
            "planner_version": PLANNER_VERSION,
            "leg_index": 0,
            "leg_direction": "buy",
            "from_asset": FROM_ASSET,
            "to_asset": TO_ASSET,
            "from_chain": CHAIN,
            "to_chain": CHAIN,
            "portfolio_id": portfolio_id_raw,
            "entry_instrument_id": instruments["USDC"]["instrument_id"],
            "target_instrument_id": instruments["AAVE"]["instrument_id"],
            "planned_amount_in": str(amount),
            "b3c_controlled_test": {
                "version": TEST_VERSION,
                "run_id": run_id,
                "status": "awaiting_swap",
            },
        },
    )
    db.add(child)
    db.flush()
    db.commit()

    return {
        "phase": "bundle_b3c_controlled_test",
        "mode": "setup_parent_child",
        "test_run_id": run_id,
        "plan_hash": plan_hash,
        "parent_intent_id": str(parent_id),
        "child_intent_id": str(child.id),
        "portfolio_id": portfolio_id_raw,
        "amount_usdc": str(amount),
        "parent_snapshot": _intent_snapshot(db, parent_id),
        "child_snapshot": _intent_snapshot(db, child.id),
        "next_step": (
            "Option B : attach_existing_swap CONFIRM=1 "
            f"CHILD_INTENT_ID={child.id} SWAP_ID=<uuid>"
        ),
    }


def mode_attach_existing_swap(db) -> dict[str, Any]:
    if not _confirm_required():
        raise RuntimeError("attach_existing_swap_requires_BUNDLE_B3C_TEST_CONFIRM=1")

    child_id = _env_uuid("CHILD_INTENT_ID")
    swap_id = _env_uuid("SWAP_ID")
    if child_id is None or swap_id is None:
        raise RuntimeError("CHILD_INTENT_ID_and_SWAP_ID_required")

    child = db.get(TransactionIntent, child_id)
    if child is None:
        raise RuntimeError("child_intent_not_found")
    swap = db.get(PersonWalletSwap, swap_id)
    if swap is None:
        raise RuntimeError("swap_not_found")

    if swap.person_id != PERSON_ID:
        raise RuntimeError("swap_person_mismatch")

    existing_link = db.execute(
        text(
            """
            SELECT id FROM transaction_intents
            WHERE linked_table = 'person_wallet_swaps' AND linked_id = :sid AND id <> :cid
            """
        ),
        {"sid": str(swap_id), "cid": str(child_id)},
    ).fetchone()
    if existing_link is not None:
        raise RuntimeError(f"swap_already_linked:intent={existing_link[0]}")

    if (swap.status or "").upper() != SwapSessionStatus.CONFIRMED.value:
        raise RuntimeError(f"swap_not_confirmed:status={swap.status}")
    if str(swap.from_asset).upper() != FROM_ASSET or str(swap.to_asset).upper() != TO_ASSET:
        raise RuntimeError("swap_asset_pair_mismatch")
    if str(swap.from_chain).lower() != CHAIN or str(swap.to_chain).lower() != CHAIN:
        raise RuntimeError("swap_chain_mismatch")

    child_meta = child.metadata_json if isinstance(child.metadata_json, dict) else {}
    portfolio_id = str(child_meta.get("portfolio_id") or "")
    batch_id = f"b3c-test-{child_meta.get('b3c_controlled_test', {}).get('run_id', uuid.uuid4().hex)[:12]}"

    audit = list(swap.audit_log) if isinstance(swap.audit_log, list) else []
    has_ctx = any(
        isinstance(e, dict) and e.get("event") == "bundle_leg_context" for e in audit
    )
    if not has_ctx:
        audit.append(
            {
                "event": "bundle_leg_context",
                "bundle_execution": True,
                "batch_id": batch_id,
                "leg_id": "leg-0",
                "portfolio_id": portfolio_id,
                "bundle_action": "invest",
                "leg_action": "rebalance_buy",
                "source": TEST_VERSION,
            }
        )
        swap.audit_log = audit
        db.add(swap)

    child.linked_table = "person_wallet_swaps"
    child.linked_id = swap_id
    test_block = dict(child_meta.get("b3c_controlled_test") or {})
    test_block["status"] = "swap_attached"
    test_block["swap_id"] = str(swap_id)
    test_block["attached_at"] = _utc_now_iso()
    child_meta["b3c_controlled_test"] = test_block
    child.metadata_json = child_meta
    db.add(child)
    db.commit()

    return {
        "phase": "bundle_b3c_controlled_test",
        "mode": "attach_existing_swap",
        "child_intent_id": str(child_id),
        "swap_id": str(swap_id),
        "batch_id": batch_id,
        "bundle_internal": is_bundle_internal_swap(swap),
        "child_snapshot": _intent_snapshot(db, child_id),
        "swap_summary": {
            "tx_hash": swap.tx_hash,
            "amount_in": str(swap.amount_in),
            "status": swap.status,
        },
        "next_step": f"settle_child CONFIRM=1 CHILD_INTENT_ID={child_id}",
    }


def mode_settle_child(db) -> dict[str, Any]:
    if not _confirm_required():
        raise RuntimeError("settle_child_requires_BUNDLE_B3C_TEST_CONFIRM=1")

    child_id = _env_uuid("CHILD_INTENT_ID")
    if child_id is None:
        raise RuntimeError("CHILD_INTENT_ID_required")

    parent_before = None
    child_row = db.get(TransactionIntent, child_id)
    if child_row and child_row.parent_intent_id:
        parent_before = _intent_snapshot(db, child_row.parent_intent_id)

    econ_before = _economic_snapshot(db)
    child_before = _intent_snapshot(db, child_id)

    os.environ["BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED"] = "true"
    repeat = os.environ.get("BUNDLE_B3C_TEST_REPEAT", "").strip() in {"1", "true", "yes", "on"}

    result_first = settle_bundle_leg_idempotently(db, child_intent_id=child_id)
    db.commit()

    result_second = None
    if repeat:
        result_second = settle_bundle_leg_idempotently(db, child_intent_id=child_id)
        db.commit()

    econ_after = _economic_snapshot(db)
    child_after = _intent_snapshot(db, child_id)
    parent_after = (
        _intent_snapshot(db, child_row.parent_intent_id)
        if child_row and child_row.parent_intent_id
        else None
    )

    settlement_block = (child_after or {}).get("bundle_leg_settlement") or {}
    checks = {
        "first_settled": result_first.settled or result_first.idempotent,
        "child_phase_ledger_settled": settlement_block.get("phase")
        == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
        "receipt_present": bool(child_after and child_after.get("settlement_receipt_hash")),
        "child_report_present": bool(child_after and child_after.get("child_report_hash")),
        "parent_unchanged": json.dumps(parent_before, sort_keys=True, default=str)
        == json.dumps(parent_after, sort_keys=True, default=str),
        "cb_unchanged": econ_after["cb"] == econ_before["cb"] == ECON_BASELINE["cb"],
        "dead_letter_zero": econ_after["dead_letter"] == 0,
        "completed_zero": econ_after["completed"] == 0,
    }
    if repeat and result_second is not None:
        checks["second_idempotent"] = result_second.idempotent is True
        checks["receipt_stable"] = (
            result_second.settlement_receipt_hash == result_first.settlement_receipt_hash
        )

    return {
        "phase": "bundle_b3c_controlled_test",
        "mode": "settle_child",
        "repeat": repeat,
        "child_intent_id": str(child_id),
        "result_first": {
            "skipped": result_first.skipped,
            "idempotent": result_first.idempotent,
            "settled": result_first.settled,
            "settlement_receipt_hash": result_first.settlement_receipt_hash,
            "child_report_hash": result_first.child_report_hash,
            "reason": result_first.reason,
        },
        "result_second": (
            {
                "skipped": result_second.skipped,
                "idempotent": result_second.idempotent,
                "settled": result_second.settled,
                "settlement_receipt_hash": result_second.settlement_receipt_hash,
                "child_report_hash": result_second.child_report_hash,
                "reason": result_second.reason,
            }
            if result_second
            else None
        ),
        "economic_before": econ_before,
        "economic_after": econ_after,
        "child_before": child_before,
        "child_after": child_after,
        "parent_before": parent_before,
        "parent_after": parent_after,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "next_step": "audit puis settle_child REPEAT=1 pour idempotence si pas déjà fait",
    }


def mode_audit(db) -> dict[str, Any]:
    parent_id = _env_uuid("PARENT_INTENT_ID")
    child_id = _env_uuid("CHILD_INTENT_ID")
    if parent_id is None or child_id is None:
        raise RuntimeError("PARENT_INTENT_ID_and_CHILD_INTENT_ID_required")

    econ = _economic_snapshot(db)
    parent = _intent_snapshot(db, parent_id)
    child = _intent_snapshot(db, child_id)
    if parent is None or child is None:
        raise RuntimeError("parent_or_child_not_found")

    swap_id = child.get("linked_id")
    swap_detail = None
    privy_debits = 0
    if swap_id:
        swap = db.get(PersonWalletSwap, uuid.UUID(swap_id))
        if swap:
            swap_detail = {
                "id": swap_id,
                "tx_hash": swap.tx_hash,
                "status": swap.status,
                "bundle_internal": is_bundle_internal_swap(swap),
                "swap_settlement_applied": swap_settlement_already_applied(swap),
                "audit_events": [
                    e.get("event")
                    for e in (swap.audit_log or [])
                    if isinstance(e, dict)
                ],
            }
            privy_debits = db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM person_wallet_deposits
                    WHERE person_id = :pid
                      AND idempotency_key LIKE :pfx
                    """
                ),
                {"pid": str(PERSON_ID), "pfx": f"lifi-swap:{swap_id}:%"},
            ).scalar()

    settlement = (child.get("bundle_leg_settlement") or {})
    checks = {
        "flags_off_service_td": _flags_snapshot()["leg_off"],
        "child_ledger_settled": settlement.get("phase") == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
        "child_receipt": bool(child.get("settlement_receipt_hash")),
        "child_report": bool(child.get("child_report_hash")),
        "parent_not_reconciled": (parent.get("current_phase") or "") != "RECONCILED",
        "parent_not_completed": (parent.get("status") or "").lower() != "completed",
        "plan_hash_match": child.get("plan_hash") == parent.get("plan_hash"),
        "pe_delta_expected": econ["pe"] >= ECON_BASELINE["pe"],
        "cb_unchanged": econ["cb"] == ECON_BASELINE["cb"],
        "dead_letter_zero": econ["dead_letter"] == 0,
        "completed_zero": econ["completed"] == 0,
    }

    return {
        "phase": "bundle_b3c_controlled_test",
        "mode": "audit",
        "parent_intent_id": str(parent_id),
        "child_intent_id": str(child_id),
        "economic": econ,
        "economic_baseline": ECON_BASELINE,
        "parent": parent,
        "child": child,
        "swap": swap_detail,
        "privy_deposit_rows_for_swap": privy_debits,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }


def mode_rollback_or_cleanup(db) -> dict[str, Any]:
    if not _confirm_required():
        raise RuntimeError("rollback_or_cleanup_requires_BUNDLE_B3C_TEST_CONFIRM=1")

    parent_id = _env_uuid("PARENT_INTENT_ID")
    child_id = _env_uuid("CHILD_INTENT_ID")
    if parent_id is None or child_id is None:
        raise RuntimeError("PARENT_INTENT_ID_and_CHILD_INTENT_ID_required")

    child = db.get(TransactionIntent, child_id)
    parent = db.get(TransactionIntent, parent_id)
    if child is None or parent is None:
        raise RuntimeError("parent_or_child_not_found")

    settlement = _existing_settlement(child)
    if settlement is not None:
        raise RuntimeError(
            "refuse_cleanup_after_settlement:ledger_economic_validated — rapport incident manuel"
        )

    child.status = IntentStatus.FAILED.value
    child_meta = child.metadata_json if isinstance(child.metadata_json, dict) else {}
    test_block = dict(child_meta.get("b3c_controlled_test") or {})
    test_block["status"] = "cleanup_failed"
    test_block["cleanup_at"] = _utc_now_iso()
    child_meta["b3c_controlled_test"] = test_block
    child.metadata_json = child_meta
    db.add(child)

    parent.status = IntentStatus.FAILED.value
    parent_meta = parent.metadata_json if isinstance(parent.metadata_json, dict) else {}
    test_block_p = dict(parent_meta.get("b3c_controlled_test") or {})
    test_block_p["status"] = "cleanup_failed"
    test_block_p["cleanup_at"] = _utc_now_iso()
    parent_meta["b3c_controlled_test"] = test_block_p
    parent.metadata_json = parent_meta
    db.add(parent)

    if child.linked_table == "person_wallet_swaps" and child.linked_id:
        child.linked_table = None
        child.linked_id = None
        db.add(child)

    db.commit()

    return {
        "phase": "bundle_b3c_controlled_test",
        "mode": "rollback_or_cleanup",
        "parent_intent_id": str(parent_id),
        "child_intent_id": str(child_id),
        "action": "marked_failed_unlinked_swap",
        "parent_snapshot": _intent_snapshot(db, parent_id),
        "child_snapshot": _intent_snapshot(db, child_id),
        "note": "Ne supprime pas ledger économique · refuse si child déjà LEDGER_SETTLED",
    }


def _existing_settlement(intent: TransactionIntent) -> dict[str, Any] | None:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    block = meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY)
    if isinstance(block, dict) and block.get("settled") is True:
        return block
    return None


def main() -> None:
    mode = (os.environ.get("BUNDLE_B3C_TEST_MODE") or "").strip().lower()
    handlers = {
        "baseline": mode_baseline,
        "setup_parent_child": mode_setup_parent_child,
        "attach_existing_swap": mode_attach_existing_swap,
        "settle_child": mode_settle_child,
        "audit": mode_audit,
        "rollback_or_cleanup": mode_rollback_or_cleanup,
    }
    if mode not in handlers:
        raise RuntimeError(
            f"invalid_mode:{mode!r} — expected one of {sorted(handlers)}"
        )

    db = SessionLocal()
    try:
        result = handlers[mode](db)
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
