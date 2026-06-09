"""Clôture contrôlée legacy batch 295804e8 — dry-run par défaut · pas de PE/CB.

Écriture uniquement si BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM=1.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text

from database import SessionLocal
from services.lifi.config import QUOTE_TTL_SECONDS
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundles.bundle_invest_lock import peek_bundle_invest_lock_state
from services.portfolio_engine.bundles.bundle_reconciliation_read_model import (
    build_bundle_reconciliation_state,
)
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit
from services.transaction_intents.lifi_intent_sync import on_swap_failed

PERSON_ID = UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
CLIENT_ID = UUID("080358a8-4519-4acf-b5da-25485446c967")
PORTFOLIO_ID = UUID("daea3720-e58e-410f-a796-3bbd541ac608")

BATCH_PREFIX = (os.environ.get("BUNDLE_LEGACY_CLOSE_BATCH_PREFIX") or "295804e8").strip().lower()
BLOCKING_ONCHAIN = frozenset({
    SwapSessionStatus.SUBMITTED.value,
})
EXPIRABLE = frozenset({
    SwapSessionStatus.QUOTE_RECEIVED.value,
    SwapSessionStatus.AWAITING_SIGNATURE.value,
    SwapSessionStatus.PENDING.value,
})


def _confirm_execute() -> bool:
    return (os.environ.get("BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM") or "").strip() in {
        "1", "true", "yes", "on",
    }


def _economic(db) -> dict[str, int]:
    return {
        "pe_atoms": int(db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar() or 0),
        "cost_basis": int(db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar() or 0),
        "lifi_swap_legs": int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM person_wallet_deposits "
                    "WHERE idempotency_key LIKE 'lifi-swap:%'"
                )
            ).scalar()
            or 0
        ),
    }


def _age_seconds(ts: datetime | None, now: datetime) -> float | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds()


def _batch_swaps(db) -> tuple[str | None, list[PersonWalletSwap]]:
    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == PERSON_ID)
        .order_by(PersonWalletSwap.created_at.asc())
        .all()
    )
    matched: list[PersonWalletSwap] = []
    batch_id: str | None = None
    for swap in swaps:
        ctx = bundle_context_from_swap_audit(swap) or {}
        bid = str(ctx.get("batch_id") or "")
        if BATCH_PREFIX not in bid:
            continue
        if batch_id is None:
            batch_id = bid
        if bid == batch_id:
            matched.append(swap)
    return batch_id, matched


def _expire_reason(swap: PersonWalletSwap, *, now: datetime) -> str | None:
    if swap.status not in EXPIRABLE:
        return None
    if swap.expires_at and swap.expires_at <= now:
        return "expires_at_passed"
    age = _age_seconds(swap.created_at, now)
    if age is not None and age > QUOTE_TTL_SECONDS:
        return f"age_gt_quote_ttl_{QUOTE_TTL_SECONDS}s"
    return None


def _swap_snapshot(swap: PersonWalletSwap, *, now: datetime) -> dict[str, Any]:
    ctx = bundle_context_from_swap_audit(swap) or {}
    age = _age_seconds(swap.created_at, now)
    return {
        "swap_id": str(swap.id),
        "status": swap.status,
        "to_asset": swap.to_asset,
        "age_seconds": round(age, 1) if age is not None else None,
        "expires_at": str(swap.expires_at) if swap.expires_at else None,
        "tx_hash": (swap.tx_hash or "").strip() or None,
        "bundle_action": ctx.get("bundle_action"),
        "leg_action": ctx.get("leg_action"),
        "expire_reason": _expire_reason(swap, now=now),
    }


def _expire_swap(db, swap: PersonWalletSwap, *, reason: str) -> dict[str, Any]:
    repo = PersonWalletSwapRepository()
    old_status = swap.status
    swap.status = SwapSessionStatus.EXPIRED.value
    swap.error_message = "Devis expiré — clôture contrôlée batch legacy."
    repo.append_audit(
        swap,
        {"event": "controlled_legacy_batch_expire", "reason": reason, "batch_prefix": BATCH_PREFIX},
    )
    on_swap_failed(db, swap)
    from services.lifi.swap_trace_service import log_swap_trace

    log_swap_trace(
        db,
        swap,
        event="expired",
        status=SwapSessionStatus.EXPIRED.value,
        error_code="quote_expired",
        message=swap.error_message,
        source="legacy_batch_close_controlled",
    )
    return {"swap_id": str(swap.id), "old_status": old_status, "new_status": swap.status, "reason": reason}


def main() -> None:
    now = datetime.now(timezone.utc)
    dry_run = not _confirm_execute()
    db = SessionLocal()
    try:
        econ_before = _economic(db)
        batch_id, swaps = _batch_swaps(db)
        snapshots = [_swap_snapshot(s, now=now) for s in swaps]

        blocking = [s for s in snapshots if s["status"] in BLOCKING_ONCHAIN]
        to_expire = [s for s in snapshots if s.get("expire_reason")]

        peek_before = peek_bundle_invest_lock_state(
            db, client_id=CLIENT_ID, portfolio_id=PORTFOLIO_ID,
        )
        recon_before = None
        if batch_id:
            try:
                recon_before = build_bundle_reconciliation_state(
                    db,
                    client_id=CLIENT_ID,
                    portfolio_id=PORTFOLIO_ID,
                    batch_id=batch_id,
                )
            except Exception as exc:
                recon_before = {"error": str(exc)}

        preflight = {
            "batch_found": batch_id is not None,
            "no_blocking_onchain": len(blocking) == 0,
            "has_expirable_legs": len(to_expire) > 0,
        }
        can_execute = all(preflight.values()) and not dry_run

        journal: list[dict[str, Any]] = []
        if can_execute:
            swap_by_id = {str(s.id): s for s in swaps}
            for snap in to_expire:
                swap = swap_by_id.get(snap["swap_id"])
                if swap is None:
                    continue
                journal.append(_expire_swap(db, swap, reason=str(snap["expire_reason"])))
            db.commit()

        econ_after = _economic(db)
        peek_after = peek_bundle_invest_lock_state(
            db, client_id=CLIENT_ID, portfolio_id=PORTFOLIO_ID,
        )
        recon_after = None
        if batch_id:
            try:
                recon_after = build_bundle_reconciliation_state(
                    db,
                    client_id=CLIENT_ID,
                    portfolio_id=PORTFOLIO_ID,
                    batch_id=batch_id,
                )
            except Exception as exc:
                recon_after = {"error": str(exc)}

        pe_delta = econ_after["pe_atoms"] - econ_before["pe_atoms"]
        cb_delta = econ_after["cost_basis"] - econ_before["cost_basis"]

        result = {
            "phase": "bundle_legacy_batch_close_controlled",
            "dry_run": dry_run,
            "batch_prefix": BATCH_PREFIX,
            "batch_id": batch_id,
            "quote_ttl_seconds": QUOTE_TTL_SECONDS,
            "pilot": {
                "portfolio_id": str(PORTFOLIO_ID),
                "client_id": str(CLIENT_ID),
                "person_id": str(PERSON_ID),
            },
            "swaps": snapshots,
            "blocking_onchain": blocking,
            "planned_expire": to_expire,
            "preflight": preflight,
            "execution_journal": journal,
            "peek_before": peek_before,
            "peek_after": peek_after,
            "reconciliation_before": recon_before,
            "reconciliation_after": recon_after,
            "economic": {
                "before": econ_before,
                "after": econ_after,
                "delta": {
                    "pe_atoms": pe_delta,
                    "cost_basis": cb_delta,
                    "lifi_swap_legs": econ_after["lifi_swap_legs"] - econ_before["lifi_swap_legs"],
                },
            },
            "checks": {
                "no_pe_mutation": pe_delta == 0,
                "no_cb_mutation": cb_delta == 0,
                "preflight_ok": all(preflight.values()),
                "dry_run_or_executed": dry_run or len(journal) > 0,
            },
            "decision": (
                "DRY_RUN_PLAN"
                if dry_run
                else ("GO_CLOSE" if pe_delta == 0 and cb_delta == 0 else "NO_GO_PE_CB_DELTA")
            ),
            "next_step": (
                "Set BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM=1 after CTO GO"
                if dry_run and all(preflight.values())
                else None
            ),
        }
        print(json.dumps(result, indent=2, default=str))
        if not dry_run and (pe_delta != 0 or cb_delta != 0):
            raise SystemExit(1)
        if not dry_run and not all(preflight.values()):
            raise SystemExit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
