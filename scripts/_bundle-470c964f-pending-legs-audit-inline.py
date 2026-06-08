"""Audit read-only — no_pending_invest_legs batch 470c964f (repro resume leg discovery)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundles.bundle_invest_lock import (
    find_active_bundle_batch_ids_for_portfolio,
    get_invest_lock,
    peek_bundle_invest_lock_state,
)
from services.portfolio_engine.bundles.orchestrator import (
    BundleOrchestrator,
    BundleOrchestratorError,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"
CLIENT_ID = "080358a8-4519-4acf-b5da-25485446c967"
PORTFOLIO_ID = "daea3720-e58e-410f-a796-3bbd541ac608"
BATCH_ID = "470c964f-e166-4b93-97c7-b184510e2523"
PARENT_INTENT_ID = "138a2de1-9ee9-41f8-80d7-70a11f03ade3"

RESUME_PENDING_STATUSES = frozenset({
    SwapSessionStatus.PENDING.value,
    SwapSessionStatus.QUOTE_RECEIVED.value,
    SwapSessionStatus.AWAITING_SIGNATURE.value,
    SwapSessionStatus.SUBMITTED.value,
})

BLOCKING_PORTFOLIO_STATUSES = frozenset({
    "PENDING",
    "QUOTE_RECEIVED",
    "AWAITING_SIGNATURE",
    "SUBMITTED",
    "CONFIRMING",
    "PROCESSING",
    "PARTIAL",
})


def _swaps_for_batch_sql(db, batch_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT s.id::text, s.status, s.to_asset, s.from_asset, s.amount_in,
                   s.created_at, s.updated_at, s.audit_log::text AS audit_log_raw
            FROM person_wallet_swaps s
            WHERE s.person_id = :person
              AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb,'[]'::jsonb)) e
                WHERE e->>'event' = 'bundle_leg_context'
                  AND e->>'batch_id' = :batch
              )
            ORDER BY s.created_at ASC
            """
        ),
        {"person": PERSON_ID, "batch": batch_id},
    ).mappings()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["audit_log"] = json.loads(item.pop("audit_log_raw") or "[]")
        except json.JSONDecodeError:
            item["audit_log"] = []
        out.append(item)
    return out


def _simulate_resume_leg_scan(db, *, batch_id: str) -> dict[str, Any]:
    person_id = UUID(PERSON_ID)
    swaps_all = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.created_at.desc())
        .limit(500)
        .all()
    )
    swaps_in_resume_statuses = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status.in_(list(RESUME_PENDING_STATUSES)),
        )
        .all()
    )

    matched: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for swap in swaps_in_resume_statuses:
        ctx = bundle_context_from_swap_audit(swap)
        reason = None
        if not ctx:
            reason = "no_bundle_leg_context_in_audit"
        elif str(ctx.get("batch_id")) != batch_id:
            reason = f"batch_mismatch:ctx={ctx.get('batch_id')}"
        else:
            action = str(ctx.get("bundle_action") or "")
            if action not in ("allocation", "invest", ""):
                reason = f"bundle_action_filtered:{action}"

        entry = {
            "swap_id": str(swap.id),
            "status": swap.status,
            "to_asset": swap.to_asset,
            "ctx_batch_id": (ctx or {}).get("batch_id"),
            "ctx_bundle_action": (ctx or {}).get("bundle_action"),
            "ctx_bundle_execution": (ctx or {}).get("bundle_execution"),
            "ctx_portfolio_id": (ctx or {}).get("portfolio_id"),
            "ctx_leg_id": (ctx or {}).get("leg_id"),
        }
        if reason:
            entry["reject_reason"] = reason
            rejected.append(entry)
        else:
            matched.append(entry)

    batch_swaps_any_status = _swaps_for_batch_sql(db, batch_id)
    status_outside_resume_filter = [
        s for s in batch_swaps_any_status if s["status"] not in RESUME_PENDING_STATUSES
    ]

    return {
        "resume_pending_statuses": sorted(RESUME_PENDING_STATUSES),
        "swaps_in_resume_statuses_total": len(swaps_in_resume_statuses),
        "matched_pending_legs": matched,
        "matched_count": len(matched),
        "rejected_from_resume_statuses": rejected,
        "batch_swaps_any_status": batch_swaps_any_status,
        "batch_swaps_outside_resume_status_filter": status_outside_resume_filter,
        "would_raise_no_pending_invest_legs": len(matched) == 0,
        "diagnosis": _diagnose(len(matched), batch_swaps_any_status, status_outside_resume_filter),
    }


def _diagnose(matched: int, batch_swaps: list, outside: list) -> list[str]:
    notes: list[str] = []
    if matched > 0:
        notes.append("resume_leg_scan_would_succeed")
        return notes
    if not batch_swaps:
        notes.append("no_swaps_linked_to_batch_in_audit_log")
        return notes
    statuses = {s["status"] for s in batch_swaps}
    if statuses and statuses.isdisjoint(RESUME_PENDING_STATUSES):
        notes.append(
            "all_batch_swaps_outside_resume_pending_statuses "
            f"(statuses={sorted(statuses)} resume_only={sorted(RESUME_PENDING_STATUSES)})"
        )
    for s in outside:
        notes.append(f"swap_{s['id'][:8]} status={s['status']} excluded_from_resume_filter")
    return notes


def main() -> None:
    db = SessionLocal()
    try:
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == UUID(PORTFOLIO_ID))
            .first()
        )
        meta = portfolio.metadata_ if portfolio else {}
        lock = get_invest_lock(meta)

        parent = db.execute(
            text(
                """
                SELECT id::text, status, metadata_json->>'batch_id' AS batch_id,
                       metadata_json->'legs' AS legs, updated_at
                FROM transaction_intents WHERE id = :parent
                """
            ),
            {"parent": PARENT_INTENT_ID},
        ).mappings().first()

        peek = peek_bundle_invest_lock_state(
            db,
            client_id=UUID(CLIENT_ID),
            portfolio_id=UUID(PORTFOLIO_ID),
        )
        active_batches = find_active_bundle_batch_ids_for_portfolio(
            db,
            client_id=UUID(CLIENT_ID),
            portfolio_id=UUID(PORTFOLIO_ID),
        )

        lock_batch = str((lock or {}).get("batch_id") or "")
        scan_lock_batch = _simulate_resume_leg_scan(db, batch_id=lock_batch or BATCH_ID)
        scan_target_batch = _simulate_resume_leg_scan(db, batch_id=BATCH_ID)

        resume_live: dict[str, Any] = {"error": None, "result": None}
        try:
            resume_live["result"] = BundleOrchestrator().resume_lifi_invest_batch(
                db,
                client_id=UUID(CLIENT_ID),
                portfolio_id=UUID(PORTFOLIO_ID),
            )
        except BundleOrchestratorError as exc:
            resume_live["error"] = str(exc)
        db.rollback()

        out = {
            "phase": "bundle_470c964f_pending_legs_audit",
            "audit_iso": datetime.now(timezone.utc).isoformat(),
            "batch_id": BATCH_ID,
            "portfolio_id": PORTFOLIO_ID,
            "parent_intent_id": PARENT_INTENT_ID,
            "answers": {
                "1_swaps_rattached": scan_target_batch["batch_swaps_any_status"],
                "2_swap_statuses": [
                    {"id": s["id"], "status": s["status"], "to_asset": s["to_asset"]}
                    for s in scan_target_batch["batch_swaps_any_status"]
                ],
                "3_no_pending_invest_legs_source": (
                    "BundleOrchestrator.resume_lifi_invest_batch "
                    "when pending==0 after filtering swaps "
                    f"status in {sorted(RESUME_PENDING_STATUSES)} "
                    "and batch_id/bundle_action match lock batch"
                ),
                "4_why_resume_misses_swaps": scan_target_batch["diagnosis"],
                "5_lock_batch_vs_scan": {
                    "lock_batch_id": lock_batch,
                    "target_batch_id": BATCH_ID,
                    "lock_matches_target": lock_batch == BATCH_ID,
                    "scan_using_lock_batch": scan_lock_batch,
                    "scan_using_target_batch": scan_target_batch,
                },
                "6_id_mismatch_check": {
                    "parent_batch_id": (dict(parent) if parent else {}).get("batch_id"),
                    "parent_status": (dict(parent) if parent else {}).get("status"),
                    "parent_legs": (dict(parent) if parent else {}).get("legs"),
                    "active_batches_portfolio": active_batches,
                    "peek": peek,
                },
                "7_pending_dump": {
                    "pending_legs_matched_by_resume_logic": scan_target_batch["matched_pending_legs"],
                    "pending_swaps_in_resume_statuses_for_person": scan_target_batch["matched_count"],
                    "rejected_candidates": scan_target_batch["rejected_from_resume_statuses"],
                    "swaps_outside_resume_status_filter": scan_target_batch[
                        "batch_swaps_outside_resume_status_filter"
                    ],
                },
            },
            "bundle_invest_lock": lock,
            "resume_live_dry_run": resume_live,
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
