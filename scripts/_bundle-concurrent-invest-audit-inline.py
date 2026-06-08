"""Audit prod — invests bundle concurrents (lecture seule)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from database import SessionLocal

PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"
PORTFOLIOS = (
    "ab4ae920-f3e8-481b-8f82-a41a81d5779d",  # Crypto Majors
    "daea3720-e58e-410f-a796-3bbd541ac608",  # Two Crypto Kings
)


def main() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    if os.environ.get("AUDIT_CUTOFF_ISO"):
        cutoff = datetime.fromisoformat(os.environ["AUDIT_CUTOFF_ISO"].replace("Z", "+00:00"))

    db = SessionLocal()
    try:
        parents = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, status, created_at, updated_at,
                           metadata_json->>'batch_id' AS batch_id,
                           metadata_json->>'portfolio_id' AS portfolio_id,
                           metadata_json->'legs' AS legs
                    FROM transaction_intents
                    WHERE person_id = :pid
                      AND product_type = 'bundle_invest'
                      AND created_at >= :cutoff
                    ORDER BY created_at DESC
                    LIMIT 20
                    """
                ),
                {"pid": PERSON_ID, "cutoff": cutoff},
            )
        ]

        locks = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, scope, asset, status, intent_id::text,
                           lock_key, product_type, created_at, expires_at, released_at
                    FROM transaction_product_locks
                    WHERE person_id = :pid
                      AND status = 'active'
                      AND released_at IS NULL
                    ORDER BY created_at DESC
                    """
                ),
                {"pid": PERSON_ID},
            )
        ]

        active_swaps = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT s.id::text, s.status, s.from_asset, s.to_asset, s.tx_hash,
                           s.created_at, s.confirmed_at,
                           (SELECT elem->>'batch_id'
                            FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                            WHERE elem->>'event' = 'bundle_leg_context'
                            LIMIT 1) AS batch_id,
                           (SELECT elem->>'portfolio_id'
                            FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                            WHERE elem->>'event' = 'bundle_leg_context'
                            LIMIT 1) AS portfolio_id
                    FROM person_wallet_swaps s
                    WHERE s.person_id = :pid
                      AND s.created_at >= :cutoff
                      AND EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                        WHERE elem->>'event' = 'bundle_leg_context'
                          AND COALESCE(elem->>'bundle_execution', 'false') = 'true'
                      )
                    ORDER BY s.created_at DESC
                    """
                ),
                {"pid": PERSON_ID, "cutoff": cutoff},
            )
        ]

        by_portfolio: dict[str, list] = {p: [] for p in PORTFOLIOS}
        for row in parents:
            pid = str(row.get("portfolio_id") or "")
            if pid in by_portfolio:
                legs = row.get("legs") or []
                confirmed = sum(
                    1 for leg in legs if isinstance(leg, dict) and str(leg.get("status")) == "confirmed"
                )
                by_portfolio[pid].append(
                    {
                        "parent_id": row["id"],
                        "batch_id": row.get("batch_id"),
                        "status": row.get("status"),
                        "legs_total": len(legs) if isinstance(legs, list) else 0,
                        "legs_confirmed": confirmed,
                        "created_at": str(row.get("created_at")),
                    }
                )

        concurrent = len([p for p in parents if str(p.get("status")) in {"partial", "submitted", "awaiting_signature"}]) >= 2

        out = {
            "phase": "bundle_concurrent_invest_audit",
            "cutoff": cutoff.isoformat(),
            "person_id": PERSON_ID,
            "concurrent_active_parents": concurrent,
            "parents_recent": parents,
            "by_portfolio": by_portfolio,
            "active_locks": locks,
            "active_lock_count": len(locks),
            "global_locks": [l for l in locks if str(l.get("asset", "")).upper() == "GLOBAL"],
            "bundle_scope_locks": [l for l in locks if str(l.get("scope", "")) == "bundle"],
            "recent_bundle_swaps": active_swaps,
            "in_flight_swaps": [
                s for s in active_swaps if str(s.get("status", "")).upper() in {"SUBMITTED", "QUOTE_RECEIVED", "PENDING"}
            ],
            "analysis": {
                "global_lock_wired_webapp": "NON — Global Lock uniquement dans B4b (flag OFF)",
                "legacy_orchestrator_parallel": concurrent,
                "expected_if_queue_worked": "2e invest bloqué 409 ou attente jusqu'à release lock",
            },
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
