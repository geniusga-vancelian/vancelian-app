#!/usr/bin/env python3
"""
Vérification read-only — forward attempt Morpho vault approve.

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.verify_morpho_vault_approve_forward --person-id <UUID>
    python3 -m scripts.verify_morpho_vault_approve_forward --ovt-id cmpsfzkac0000ad0155fsvubv
    python3 -m scripts.verify_morpho_vault_approve_forward --hours 24
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

import sqlalchemy as sa
from database import SessionLocal
from services.transaction_attempts.reconciliation import (
    migration_171_ready,
    scan_attempt_gaps_for_person,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Morpho vault approve forward attempts.")
    parser.add_argument("--person-id", type=str, default=None)
    parser.add_argument("--ovt-id", type=str, default=None, help="OVT approve id to check")
    parser.add_argument("--hours", type=int, default=48, help="Lookback for recent approve OVTs")
    return parser.parse_args()


def main() -> int:
    if not migration_171_ready():
        print(json.dumps({"ready": False, "message": "Migration 171 requise."}, indent=2))
        return 1

    args = _parse_args()
    since = datetime.now(timezone.utc) - timedelta(hours=max(args.hours, 1))
    db = SessionLocal()
    try:
        sql = """
            SELECT id, person_id, operation, status, tx_hash, chain_id, group_key,
                   idempotency_key, integration_mode, created_at
            FROM onchain_vault_transactions
            WHERE integration_mode = 'direct_morpho'
              AND operation = 'approve'
              AND status = 'success'
              AND tx_hash IS NOT NULL
        """
        params: dict = {"since": since}
        if args.ovt_id:
            sql += " AND id = :ovt_id"
            params["ovt_id"] = args.ovt_id
        else:
            sql += " AND created_at >= :since"
        if args.person_id:
            sql += " AND person_id = :person_id"
            params["person_id"] = args.person_id
        sql += " ORDER BY created_at DESC LIMIT 20"

        ovts = db.execute(sa.text(sql), params).mappings().all()
        rows = []
        missing_attempt = []
        for ovt in ovts:
            attempt = db.execute(
                sa.text(
                    """
                    SELECT id::text, protocol, step_type, status, tx_hash, intent_id::text,
                           linked_reference_id, group_key,
                           metadata_json->>'dual_write_source' AS dual_write_source
                    FROM onchain_transaction_attempts
                    WHERE linked_reference_id = :ovt_id
                       OR (chain_id = :chain_id AND tx_hash = :tx_hash AND step_type = 'approve')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "ovt_id": ovt["id"],
                    "chain_id": int(ovt["chain_id"] or 8453),
                    "tx_hash": str(ovt["tx_hash"]).strip().lower(),
                },
            ).mappings().first()

            intent = db.execute(
                sa.text(
                    """
                    SELECT id::text FROM transaction_intents
                    WHERE linked_reference_id = :ovt_id
                    LIMIT 1
                    """
                ),
                {"ovt_id": ovt["id"]},
            ).fetchone()

            item = {
                "ovt_id": ovt["id"],
                "person_id": str(ovt["person_id"]),
                "tx_hash": ovt["tx_hash"],
                "group_key": ovt.get("group_key") or ovt.get("idempotency_key"),
                "created_at": ovt["created_at"].isoformat() if ovt.get("created_at") else None,
                "attempt": dict(attempt) if attempt else None,
                "intent_for_approve_ovt": intent[0] if intent else None,
            }
            rows.append(item)
            if attempt is None:
                missing_attempt.append(ovt["id"])

        gap_hits: list[dict] = []
        person_ids = {str(r["person_id"]) for r in rows}
        if args.person_id:
            person_ids.add(args.person_id)
        for pid in person_ids:
            try:
                gaps = scan_attempt_gaps_for_person(db, UUID(pid))
            except Exception:
                continue
            for g in gaps:
                if g.get("gap_type") != "vault_tx_missing_attempt":
                    continue
                ref = g.get("reference_id")
                if ref in {r["ovt_id"] for r in rows} or (args.ovt_id and ref == args.ovt_id):
                    gap_hits.append({"person_id": pid, **g})

        payload = {
            "ready": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "since_utc": since.isoformat(),
            "approve_ovts_checked": len(rows),
            "missing_forward_attempt": missing_attempt,
            "gap_report_hits_on_checked_ovts": gap_hits,
            "rows": rows,
            "ok": len(missing_attempt) == 0 and len(gap_hits) == 0,
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if payload["ok"] else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
