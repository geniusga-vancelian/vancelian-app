#!/usr/bin/env python3
"""
Rapport attempts dual-write forward (hors backfill) — local/dev.

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.phase2_forward_dual_write_report
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

import sqlalchemy as sa
from database import SessionLocal, engine
from services.transaction_attempts.reconciliation import migration_171_ready


def main() -> int:
    if not migration_171_ready():
        print(json.dumps({"ready": False, "message": "Migration 171 requise."}, indent=2))
        return 1

    db = SessionLocal()
    try:
        forward = db.execute(
            sa.text(
                """
                SELECT id, protocol, step_type, status, tx_hash, intent_id, group_key,
                       linked_table, linked_id, linked_reference_id, metadata_json
                FROM onchain_transaction_attempts
                WHERE metadata_json->>'dual_write_source' IS NOT NULL
                  AND COALESCE(metadata_json->>'backfill', 'false') != 'true'
                ORDER BY created_at DESC
                """
            )
        ).mappings().all()

        backfill_count = db.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM onchain_transaction_attempts
                WHERE metadata_json->>'backfill' = 'true'
                   OR idempotency_key LIKE 'backfill:chain:%'
                """
            )
        ).scalar()
        privy_count = db.execute(
            sa.text("SELECT COUNT(*) FROM onchain_transaction_attempts WHERE protocol = 'privy'")
        ).scalar()
        dup_tx = db.execute(
            sa.text(
                """
                SELECT chain_id, tx_hash, COUNT(*) AS c
                FROM onchain_transaction_attempts
                WHERE tx_hash IS NOT NULL
                GROUP BY chain_id, tx_hash
                HAVING COUNT(*) > 1
                """
            )
        ).mappings().all()

        by_protocol: dict[str, int] = {}
        by_status: dict[str, int] = {}
        rows = []
        for row in forward:
            p = row["protocol"]
            s = row["status"]
            by_protocol[p] = by_protocol.get(p, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1
            meta = row["metadata_json"] if isinstance(row["metadata_json"], dict) else {}
            rows.append(
                {
                    "protocol": p,
                    "step_type": row["step_type"],
                    "status": s,
                    "tx_hash": row["tx_hash"],
                    "intent_id": str(row["intent_id"]) if row["intent_id"] else None,
                    "group_key": row["group_key"],
                    "linked_table": row["linked_table"],
                    "linked_id": str(row["linked_id"]) if row["linked_id"] else None,
                    "linked_reference_id": row["linked_reference_id"],
                    "dual_write_source": meta.get("dual_write_source"),
                }
            )

        payload = {
            "ready": True,
            "forward_attempts_total": len(forward),
            "backfill_attempts_total": backfill_count,
            "privy_attempts_total": privy_count,
            "by_protocol": by_protocol,
            "by_status": by_status,
            "duplicate_chain_tx_groups": [dict(r) for r in dup_tx],
            "attempts": rows[:100],
            "anomalies": [],
        }
        if dup_tx:
            payload["anomalies"].append(
                "duplicate_chain_id_tx_hash: plusieurs attempts pour le même hash — investiguer"
            )
        if privy_count:
            payload["anomalies"].append("privy_attempts_present")

        print(json.dumps(payload, indent=2, default=str))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
