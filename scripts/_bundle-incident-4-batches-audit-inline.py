"""Audit prod read-only — incident 4 batches bundle invest (gaelitier)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from database import SessionLocal
from services.product_locks.enums import ProductLockScope

PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"
CLIENT_EMAIL = "gaelitier@gmail.com"

INCIDENT_BATCHES: tuple[dict[str, str], ...] = (
    {
        "batch_prefix": "94d810b4",
        "label": "nouveau",
        "portfolio_id": "ab4ae920-f3e8-481b-8f82-a41a81d5779d",
        "portfolio_name": "Crypto Majors",
        "recovery_order": "1",
    },
    {
        "batch_prefix": "470c964f",
        "label": "nouveau",
        "portfolio_id": "daea3720-e58e-410f-a796-3bbd541ac608",
        "portfolio_name": "Two Crypto Kings",
        "recovery_order": "2",
    },
    {
        "batch_prefix": "10d688bb",
        "label": "ancien",
        "portfolio_id": "ab4ae920-f3e8-481b-8f82-a41a81d5779d",
        "portfolio_name": "Crypto Majors",
        "recovery_order": "3",
    },
    {
        "batch_prefix": "3e7c5db4",
        "label": "ancien",
        "portfolio_id": "daea3720-e58e-410f-a796-3bbd541ac608",
        "portfolio_name": "Two Crypto Kings",
        "recovery_order": "4",
    },
)

PE_BASELINE = int(os.environ.get("INCIDENT_PE_BASELINE", "19"))
CB_BASELINE = int(os.environ.get("INCIDENT_CB_BASELINE", "67"))
LEGS_BASELINE = int(os.environ.get("INCIDENT_LEGS_BASELINE", "131"))


def _flag_on(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _leg_counts(legs: list[Any] | None) -> dict[str, int]:
    counts = {
        "expected": 0,
        "confirmed": 0,
        "submitted": 0,
        "awaiting_signature": 0,
        "pending": 0,
        "failed": 0,
        "expired": 0,
        "other": 0,
    }
    if not isinstance(legs, list):
        return counts
    counts["expected"] = len(legs)
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        st = str(leg.get("status") or "").lower()
        if st == "confirmed":
            counts["confirmed"] += 1
        elif st == "submitted":
            counts["submitted"] += 1
        elif st in {"awaiting_signature", "signature_requested", "pending_signature"}:
            counts["awaiting_signature"] += 1
        elif st == "pending":
            counts["pending"] += 1
        elif st == "failed":
            counts["failed"] += 1
        elif st == "expired":
            counts["expired"] += 1
        else:
            counts["other"] += 1
    return counts


def _classify_batch(*, parent_status: str | None, leg_counts: dict[str, int], lock: dict | None) -> str:
    st = str(parent_status or "").lower()
    if st in {"confirmed", "completed"}:
        return "terminal_completed"
    if st in {"failed", "expired", "cancelled"}:
        return "terminal_failed"
    if leg_counts["awaiting_signature"] or leg_counts["pending"] or leg_counts["submitted"]:
        return "stuck_in_progress"
    if lock and str(lock.get("status", "")).lower() in {
        "pending_signature",
        "signature_requested",
        "submitted",
        "pending_confirmation",
        "partial_pending",
        "finalizing",
    }:
        return "stuck_in_progress"
    if st in {"partial", "awaiting_signature", "submitted", "partial_pending"}:
        return "stuck_in_progress"
    if st == "created":
        return "orphan_created"
    return "unknown"


def main() -> None:
    audit_iso = datetime.now(timezone.utc).isoformat()
    db = SessionLocal()
    try:
        pe_total = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
        cb_total = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
        legs_total = db.execute(
            text(
                "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
            )
        ).scalar()

        outbox_rows = db.execute(
            text(
                """
                SELECT status, COUNT(*)::int AS n
                FROM transaction_outbox
                GROUP BY status
                """
            )
        ).fetchall()
        outbox = {str(row[0]): int(row[1]) for row in outbox_rows}
        dead_letter = int(outbox.get("dead_letter", 0))

        global_locks = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, status, intent_id::text, created_at, released_at
                    FROM transaction_product_locks
                    WHERE person_id = :pid
                      AND scope = :scope
                      AND asset = 'GLOBAL'
                    ORDER BY created_at DESC
                    LIMIT 20
                    """
                ),
                {"pid": PERSON_ID, "scope": ProductLockScope.FINANCIAL_TRANSACTION.value},
            )
        ]
        active_global = [g for g in global_locks if g.get("released_at") is None and g.get("status") == "active"]

        batch_reports: list[dict[str, Any]] = []
        for spec in INCIDENT_BATCHES:
            prefix = spec["batch_prefix"]
            portfolio_id = spec["portfolio_id"]

            parent = db.execute(
                text(
                    """
                    SELECT id::text, status, created_at, updated_at,
                           metadata_json->>'batch_id' AS batch_id,
                           metadata_json->>'portfolio_id' AS portfolio_id,
                           metadata_json->'legs' AS legs,
                           metadata_json->>'funding_amount' AS funding_amount
                    FROM transaction_intents
                    WHERE person_id = :pid
                      AND product_type = 'bundle_invest'
                      AND metadata_json->>'batch_id' LIKE :prefix
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"pid": PERSON_ID, "prefix": f"{prefix}%"},
            ).mappings().first()

            portfolio_row = db.execute(
                text(
                    """
                    SELECT id::text, name, metadata::text AS metadata_raw
                    FROM pe_portfolios
                    WHERE id = :pid
                    """
                ),
                {"pid": portfolio_id},
            ).mappings().first()

            lock_meta = None
            if portfolio_row and portfolio_row.get("metadata_raw"):
                meta = json.loads(portfolio_row["metadata_raw"])
                lock_meta = meta.get("bundle_invest_lock")
                if lock_meta and not str(lock_meta.get("batch_id", "")).startswith(prefix):
                    lock_meta = {"note": "portfolio_lock_other_batch", "lock": lock_meta}

            legs = (parent or {}).get("legs") if parent else None
            leg_counts = _leg_counts(legs if isinstance(legs, list) else None)
            batch_id = (parent or {}).get("batch_id")

            swaps = [
                dict(r._mapping)
                for r in db.execute(
                    text(
                        """
                        SELECT s.id::text, s.status, s.from_asset, s.to_asset, s.tx_hash,
                               s.created_at, s.confirmed_at,
                               (SELECT elem->>'leg_id'
                                FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                                WHERE elem->>'event' = 'bundle_leg_context'
                                LIMIT 1) AS leg_id
                        FROM person_wallet_swaps s
                        WHERE s.person_id = :person
                          AND EXISTS (
                            SELECT 1
                            FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                            WHERE elem->>'event' = 'bundle_leg_context'
                              AND elem->>'batch_id' LIKE :prefix
                          )
                        ORDER BY s.created_at ASC
                        """
                    ),
                    {"person": PERSON_ID, "prefix": f"{prefix}%"},
                )
            ]

            batch_reports.append(
                {
                    "recovery_order": spec["recovery_order"],
                    "batch_prefix": prefix,
                    "batch_id": batch_id,
                    "label": spec["label"],
                    "portfolio_id": portfolio_id,
                    "portfolio_name": spec["portfolio_name"],
                    "parent_intent_id": (parent or {}).get("id"),
                    "parent_status": (parent or {}).get("status"),
                    "funding_amount": (parent or {}).get("funding_amount"),
                    "created_at": str((parent or {}).get("created_at")) if parent else None,
                    "updated_at": str((parent or {}).get("updated_at")) if parent else None,
                    "portfolio_lock_metadata": lock_meta,
                    "global_lock_active_for_intent": [
                        g for g in active_global if g.get("intent_id") == (parent or {}).get("id")
                    ],
                    "leg_counts": leg_counts,
                    "legs_detail": legs,
                    "swaps": swaps,
                    "classification": _classify_batch(
                        parent_status=(parent or {}).get("status"),
                        leg_counts=leg_counts,
                        lock=lock_meta if isinstance(lock_meta, dict) else None,
                    ),
                    "ui_resume_hint": (
                        f"Batch {prefix}… — {spec['portfolio_name']} — "
                        f"{leg_counts['confirmed']}/{leg_counts['expected']} legs confirmés"
                    ),
                }
            )

        stuck = [b for b in batch_reports if b["classification"] == "stuck_in_progress"]
        terminal = [b for b in batch_reports if b["classification"].startswith("terminal")]

        out = {
            "phase": "bundle_incident_4_batches_audit",
            "audit_iso": audit_iso,
            "person_id": PERSON_ID,
            "account": CLIENT_EMAIL,
            "td_note": "arquantix-api:161",
            "global_user_transaction_lock_enabled": os.environ.get(
                "GLOBAL_USER_TRANSACTION_LOCK_ENABLED"
            ),
            "flag_global_lock_off": not _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED"),
            "active_global_locks": active_global,
            "active_global_lock_count": len(active_global),
            "pe_atoms_total": pe_total,
            "pe_atoms_delta_vs_baseline": int(pe_total) - PE_BASELINE,
            "cost_basis_total": cb_total,
            "cost_basis_delta_vs_baseline": int(cb_total) - CB_BASELINE,
            "lifi_swap_deposits_total": legs_total,
            "lifi_legs_delta_vs_baseline": int(legs_total) - LEGS_BASELINE,
            "outbox_by_status": outbox,
            "dead_letter_count": dead_letter,
            "batches": batch_reports,
            "summary": {
                "total_incident_batches": len(batch_reports),
                "stuck_count": len(stuck),
                "terminal_count": len(terminal),
                "recovery_order": [b["batch_prefix"] for b in sorted(batch_reports, key=lambda x: x["recovery_order"])],
                "do_not_parallel_recovery": True,
                "global_lock_activatable_after_recovery": len(stuck) == 0 and dead_letter == 0,
            },
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
