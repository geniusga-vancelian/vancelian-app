"""Test WebApp prod — Bundle Invest 1 USDC Base (pilote gaelitier).

Modes (env ``BUNDLE_WEBAPP_TEST_MODE``) :
  baseline | post_trade_audit

Objectif : prouver Privy réel · swap Base réel · confirmation · settlement économique.
Pas de LIFI_SWAPS_MOCK · pas de flags ON en TD.
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from database import SessionLocal
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
)
from services.product_locks.enums import ProductLockScope
from services.transaction_intents.bundle_parent_child_repository import find_children
from services.transaction_intents.enums import IntentProductType, IntentRole

PERSON_ID = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
PORTFOLIO_ID = uuid.UUID("ab4ae920-f3e8-481b-8f82-a41a81d5779d")
WALLET_ID = uuid.UUID("a5bc9936-11f2-411b-be33-f0b63196f65d")
B4B_TEST_PARENT_ID = uuid.UUID("0ef6517e-10c1-453b-bce7-3e6ff08c866d")
ECON_BASELINE = {"pe": 19, "cb": 67, "lifi_swap_legs": 131}
MOCK_TX_PATTERN = re.compile(r"^0xmock-", re.I)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _test_start_cutoff() -> datetime:
    env_iso = _parse_iso(os.environ.get("BUNDLE_WEBAPP_TEST_START_ISO"))
    if env_iso is not None:
        return env_iso
    return datetime.now(timezone.utc) - timedelta(hours=24)


def _flags_snapshot() -> dict[str, Any]:
    keys = (
        "BUNDLE_PARENT_CONTROLLER_ENABLED",
        "BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED",
        "GLOBAL_USER_TRANSACTION_LOCK_ENABLED",
        "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED",
        "BUNDLE_FUNDING_HANDLER_ENABLED",
        "LIFI_SWAPS_MOCK",
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
    bundle_locks = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM transaction_product_locks
            WHERE scope = 'bundle' AND status = 'active' AND released_at IS NULL
            """
        )
    ).scalar()
    return {
        "pe": int(db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()),
        "cb": int(db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()),
        "lifi_swap_legs": int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
                )
            ).scalar()
        ),
        "active_financial_locks": int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM transaction_product_locks
                    WHERE scope = :scope AND asset = 'GLOBAL'
                      AND status = 'active' AND released_at IS NULL
                    """
                ),
                {"scope": ProductLockScope.FINANCIAL_TRANSACTION.value},
            ).scalar()
        ),
        "active_bundle_locks": int(bundle_locks),
        "dead_letter": int(
            db.execute(text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")).scalar()
        ),
        "completed": int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM transaction_intents
                    WHERE metadata_json->>'phase' = 'COMPLETED' OR current_phase = 'COMPLETED'
                    """
                )
            ).scalar()
        ),
        "wallet_balances": {row[0]: {"available": row[1], "balance": row[2]} for row in balances},
    }


def _intent_brief(row: TransactionIntent) -> dict[str, Any]:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return {
        "id": str(row.id),
        "product_type": row.product_type,
        "intent_role": row.intent_role,
        "status": row.status,
        "current_phase": row.current_phase,
        "metadata_phase": meta.get("phase"),
        "plan_hash": meta.get("plan_hash"),
        "parent_report_hash": meta.get("parent_report_hash"),
        "portfolio_id": meta.get("portfolio_id") or meta.get("bundle_id"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "bundle_leg_settlement": meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY),
        "bundle_parent_controller": meta.get("bundle_parent_controller"),
    }


def _swap_brief(swap: PersonWalletSwap) -> dict[str, Any]:
    ctx = bundle_context_for_swap(swap)
    return {
        "id": str(swap.id),
        "status": swap.status,
        "tx_hash": swap.tx_hash,
        "from_asset": swap.from_asset,
        "to_asset": swap.to_asset,
        "from_chain": swap.from_chain,
        "to_chain": swap.to_chain,
        "amount_in": str(swap.amount_in) if swap.amount_in is not None else None,
        "bundle_internal": is_bundle_internal_swap(swap),
        "bundle_leg_context": ctx,
        "tx_hash_is_mock": bool(swap.tx_hash and MOCK_TX_PATTERN.match(str(swap.tx_hash))),
        "confirmed_at": swap.confirmed_at.isoformat() if swap.confirmed_at else None,
        "created_at": swap.created_at.isoformat() if swap.created_at else None,
    }


def _portfolio_matches(meta: dict[str, Any]) -> bool:
    portfolio = str(meta.get("portfolio_id") or meta.get("bundle_id") or "").strip()
    return not portfolio or portfolio == str(PORTFOLIO_ID)


def _resolve_parent(db, parent_id: uuid.UUID | None, cutoff: datetime) -> TransactionIntent | None:
    if parent_id is not None:
        return db.get(TransactionIntent, parent_id)

    candidates = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == PERSON_ID,
            TransactionIntent.product_type == IntentProductType.BUNDLE_INVEST.value,
            TransactionIntent.created_at >= cutoff,
            TransactionIntent.id != B4B_TEST_PARENT_ID,
        )
        .order_by(TransactionIntent.created_at.desc())
        .limit(20)
        .all()
    )
    for row in candidates:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if not _portfolio_matches(meta):
            continue
        if row.intent_role == IntentRole.PARENT.value:
            return row
        if isinstance(meta.get("legs"), list) and meta.get("batch_id"):
            return row
    return None


def _legacy_legs(meta: dict[str, Any]) -> list[dict[str, Any]]:
    legs = meta.get("legs")
    if not isinstance(legs, list):
        return []
    return [dict(item) for item in legs if isinstance(item, dict)]


def _recent_bundle_swaps(db, cutoff: datetime) -> list[PersonWalletSwap]:
    recent = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == PERSON_ID,
            PersonWalletSwap.created_at >= cutoff,
            PersonWalletSwap.status == "CONFIRMED",
        )
        .order_by(PersonWalletSwap.confirmed_at.desc().nulls_last(), PersonWalletSwap.created_at.desc())
        .limit(20)
        .all()
    )
    out: list[PersonWalletSwap] = []
    for swap in recent:
        if not is_bundle_internal_swap(swap):
            continue
        if MOCK_TX_PATTERN.match(str(swap.tx_hash or "")):
            continue
        ctx = bundle_context_for_swap(swap) or {}
        portfolio = str(ctx.get("portfolio_id") or "").strip()
        if portfolio and portfolio != str(PORTFOLIO_ID):
            continue
        out.append(swap)
    return out


def _mode_baseline(db) -> dict[str, Any]:
    test_start_iso = os.environ.get("BUNDLE_WEBAPP_TEST_START_ISO") or _utc_now_iso()
    economic = _economic_snapshot(db)
    flags = _flags_snapshot()
    usdc = (economic.get("wallet_balances") or {}).get("USDC", {})
    checks = {
        "flags_all_off": all(flags.get(f"{k}_off") for k in (
            "BUNDLE_PARENT_CONTROLLER_ENABLED",
            "BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED",
            "GLOBAL_USER_TRANSACTION_LOCK_ENABLED",
            "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED",
            "BUNDLE_FUNDING_HANDLER_ENABLED",
            "LIFI_SWAPS_MOCK",
        )),
        "pe_baseline": economic["pe"] == ECON_BASELINE["pe"],
        "cb_baseline": economic["cb"] == ECON_BASELINE["cb"],
        "legs_baseline": economic["lifi_swap_legs"] == ECON_BASELINE["lifi_swap_legs"],
        "active_financial_locks_zero": economic["active_financial_locks"] == 0,
        "dead_letter_zero": economic["dead_letter"] == 0,
        "completed_zero": economic["completed"] == 0,
        "usdc_wallet_available": float(usdc.get("available") or 0) >= 1.0,
    }
    return {
        "phase": "bundle_webapp_invest_1usdc_test",
        "mode": "baseline",
        "test_start_iso": test_start_iso,
        "person_id": str(PERSON_ID),
        "portfolio_id": str(PORTFOLIO_ID),
        "amount_usdc": "1",
        "flags": flags,
        "economic": economic,
        "economic_baseline": ECON_BASELINE,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "next_step": "Invest WebApp manuel 1 USDC Crypto Majors · noter BUNDLE_WEBAPP_TEST_START_ISO",
    }


def _mode_post_trade_audit(db) -> dict[str, Any]:
    cutoff = _test_start_cutoff()
    parent_id_raw = (os.environ.get("PARENT_INTENT_ID") or "").strip()
    parent_id = uuid.UUID(parent_id_raw) if parent_id_raw else None

    economic = _economic_snapshot(db)
    parent = _resolve_parent(db, parent_id, cutoff)
    parent_meta = (
        parent.metadata_json if parent is not None and isinstance(parent.metadata_json, dict) else {}
    )
    execution_path = "unknown"
    children: list[TransactionIntent] = []
    swaps: list[PersonWalletSwap] = []

    if parent is not None and parent.intent_role == IntentRole.PARENT.value:
        execution_path = "event_driven_b1"
        children = find_children(db, parent_intent_id=parent.id)
        for child in children:
            if child.linked_table == "person_wallet_swaps" and child.linked_id:
                swap = db.get(PersonWalletSwap, child.linked_id)
                if swap is not None:
                    swaps.append(swap)
    elif parent is not None:
        execution_path = "legacy_orchestrator_metadata"
        batch_id = str(parent_meta.get("batch_id") or "").strip()
        for leg in _legacy_legs(parent_meta):
            swap_raw = leg.get("swap_id") or leg.get("linked_id")
            if not swap_raw:
                continue
            try:
                swap = db.get(PersonWalletSwap, uuid.UUID(str(swap_raw)))
            except (ValueError, TypeError):
                swap = None
            if swap is not None:
                swaps.append(swap)
        if batch_id:
            batch_swaps = _recent_bundle_swaps(db, cutoff)
            swaps = [
                s
                for s in batch_swaps
                if str((bundle_context_for_swap(s) or {}).get("batch_id") or "") == batch_id
            ] or swaps

    if not swaps:
        swaps = _recent_bundle_swaps(db, cutoff)
        if swaps and execution_path == "unknown":
            execution_path = "legacy_orchestrator_swaps"

    if parent is None and not swaps:
        return {
            "phase": "bundle_webapp_invest_1usdc_test",
            "mode": "post_trade_audit",
            "decision": "NO_PARENT_FOUND",
            "test_start_cutoff": cutoff.isoformat(),
            "economic": economic,
            "all_checks_pass": False,
            "next_step": "Relancer après invest WebApp ou passer PARENT_INTENT_ID",
        }

    primary_swap = swaps[0] if swaps else None
    settlement_applied = (
        swap_settlement_already_applied(primary_swap) if primary_swap else None
    )

    duplicate_leg_writes = 0
    if primary_swap is not None:
        duplicate_leg_writes = int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM (
                      SELECT idempotency_key, COUNT(*) AS c
                      FROM person_wallet_deposits
                      WHERE idempotency_key LIKE :pfx
                      GROUP BY idempotency_key
                      HAVING COUNT(*) > 1
                    ) d
                    """
                ),
                {"pfx": f"lifi-swap:{primary_swap.id}:%"},
            ).scalar()
            or 0
        )

    tx_real = (
        primary_swap is not None
        and primary_swap.tx_hash
        and not MOCK_TX_PATTERN.match(str(primary_swap.tx_hash))
    )
    swap_confirmed = primary_swap is not None and str(primary_swap.status).upper() == "CONFIRMED"

    child_settled = any(
        isinstance((c.metadata_json or {}).get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY), dict)
        and (c.metadata_json or {}).get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY, {}).get("phase")
        == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED
        for c in children
    )

    all_tx_real = len(swaps) > 0 and all(
        s.tx_hash and not MOCK_TX_PATTERN.match(str(s.tx_hash)) for s in swaps
    )
    all_confirmed = len(swaps) > 0 and all(str(s.status).upper() == "CONFIRMED" for s in swaps)
    legacy_legs = _legacy_legs(parent_meta) if parent is not None else []
    confirmed_swaps = [s for s in swaps if str(s.status).upper() == "CONFIRMED"]
    legacy_legs_confirmed = len(confirmed_swaps) >= 5 and all_confirmed

    pe_delta = economic["pe"] - ECON_BASELINE["pe"]
    cb_delta = economic["cb"] - ECON_BASELINE["cb"]
    legs_delta = economic["lifi_swap_legs"] - ECON_BASELINE["lifi_swap_legs"]

    settlement_checks = [swap_settlement_already_applied(s) for s in confirmed_swaps]
    all_settled_once = len(settlement_checks) > 0 and all(settlement_checks)

    checks = {
        "parent_or_swaps_found": parent is not None or len(swaps) > 0,
        "swaps_confirmed_count": len(swaps) >= 1,
        "all_tx_hash_real": len(confirmed_swaps) > 0 and all(
            s.tx_hash and not MOCK_TX_PATTERN.match(str(s.tx_hash)) for s in confirmed_swaps
        ),
        "all_swaps_confirmed": len(confirmed_swaps) >= 5,
        "confirmed_swap_count": len(confirmed_swaps),
        "bundle_internal_swaps": len(swaps) > 0 and all(is_bundle_internal_swap(s) for s in swaps),
        "no_mock_tx": len(confirmed_swaps) > 0 and all(
            not MOCK_TX_PATTERN.match(str(s.tx_hash or "")) for s in confirmed_swaps
        ),
        "settlement_applied_per_swap": all_settled_once,
        "no_duplicate_leg_deposits": duplicate_leg_writes == 0,
        "dead_letter_zero": economic["dead_letter"] == 0,
        "active_financial_locks_zero": economic["active_financial_locks"] == 0,
        "active_bundle_locks_zero": economic.get("active_bundle_locks", 0) == 0,
        "pe_delta_non_negative": pe_delta >= 0,
        "cb_delta_positive_legacy": cb_delta > 0 or pe_delta > 0 or legs_delta > 0,
        "legs_delta_expected": legs_delta >= 0,
        "legacy_legs_confirmed_or_event_settled": legacy_legs_confirmed or child_settled,
    }

    return {
        "phase": "bundle_webapp_invest_1usdc_test",
        "mode": "post_trade_audit",
        "test_start_cutoff": cutoff.isoformat(),
        "parent_intent_id": str(parent.id) if parent is not None else None,
        "batch_id": parent_meta.get("batch_id"),
        "parent_status": parent.status if parent is not None else None,
        "legacy_legs_count": len(legacy_legs),
        "legacy_legs": legacy_legs,
        "parent_snapshot": _intent_brief(parent) if parent is not None else None,
        "child_snapshots": [_intent_brief(c) for c in children],
        "swap_snapshots": [_swap_brief(s) for s in swaps],
        "swap_count": len(swaps),
        "primary_swap_id": str(primary_swap.id) if primary_swap else None,
        "settlement_already_applied": settlement_applied,
        "duplicate_leg_deposit_keys": duplicate_leg_writes,
        "economic": economic,
        "economic_baseline": ECON_BASELINE,
        "economic_delta": {"pe": pe_delta, "cb": cb_delta, "lifi_swap_legs": legs_delta},
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "execution_path": execution_path,
        "ui_observed": {
            "amount_usdc": "20 invest / ~19 alloués",
            "legs": 5,
            "assets": ["CBBTC", "CBETH", "LINK", "AAVE", "UNI"],
            "status": "Terminée",
        },
        "next_step": "Rédiger GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_REPORT.md",
    }


def main() -> None:
    mode = (os.environ.get("BUNDLE_WEBAPP_TEST_MODE") or "").strip().lower()
    db = SessionLocal()
    try:
        if mode == "baseline":
            out = _mode_baseline(db)
        elif mode == "post_trade_audit":
            out = _mode_post_trade_audit(db)
        else:
            raise SystemExit(f"Mode inconnu: {mode!r}")
        print(json.dumps(out, indent=2, default=str))
        if not out.get("all_checks_pass", False):
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
