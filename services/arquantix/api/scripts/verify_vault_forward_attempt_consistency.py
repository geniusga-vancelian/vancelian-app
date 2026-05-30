#!/usr/bin/env python3
"""
Détecte les OVT vault success avec tx_hash dont l'attempt forward est incohérent.

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.verify_vault_forward_attempt_consistency
    python3 -m scripts.verify_vault_forward_attempt_consistency --person-id <UUID>
    python3 -m scripts.verify_vault_forward_attempt_consistency --ovt-id cmpsidbte0002ad01tubyadpc
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

import sqlalchemy as sa
from database import SessionLocal
from services.transaction_attempts.reconciliation import migration_171_ready


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--person-id", type=str, default=None)
    parser.add_argument("--ovt-id", type=str, default=None)
    parser.add_argument("--hours", type=int, default=48)
    args = parser.parse_args()

    if not migration_171_ready():
        print(json.dumps({"ready": False, "message": "Migration 171 requise."}, indent=2))
        return 1

    since = datetime.now(timezone.utc) - timedelta(hours=max(args.hours, 1))
    db = SessionLocal()
    try:
        sql = """
            SELECT o.id, o.person_id, o.operation, o.status, o.tx_hash, o.integration_mode,
                   o.created_at,
                   a.id::text AS attempt_id,
                   a.protocol,
                   a.step_type,
                   a.status AS attempt_status,
                   a.tx_hash AS attempt_tx_hash,
                   a.metadata_json->>'dual_write_source' AS dual_write_source
            FROM onchain_vault_transactions o
            LEFT JOIN onchain_transaction_attempts a
              ON a.linked_reference_id = o.id
             AND a.step_type = o.operation::text
            WHERE o.status = 'success'
              AND o.tx_hash IS NOT NULL
              AND o.integration_mode IN ('direct_morpho', 'ledgity_vault')
        """
        params: dict = {"since": since}
        if args.ovt_id:
            sql += " AND o.id = :ovt_id"
            params["ovt_id"] = args.ovt_id
        else:
            sql += " AND o.created_at >= :since"
        if args.person_id:
            sql += " AND o.person_id = :person_id"
            params["person_id"] = args.person_id
        sql += " ORDER BY o.created_at DESC LIMIT 100"

        rows = db.execute(sa.text(sql), params).mappings().all()
        inconsistent = []
        ok_rows = []
        for row in rows:
            item = dict(row)
            attempt_id = item.get("attempt_id")
            attempt_status = (item.get("attempt_status") or "").strip().lower()
            attempt_tx = item.get("attempt_tx_hash")
            if attempt_id is None:
                inconsistent.append({**item, "reason": "missing_attempt"})
            elif attempt_status != "confirmed" or not attempt_tx:
                inconsistent.append(
                    {
                        **item,
                        "reason": "attempt_not_confirmed_or_missing_tx_hash",
                    }
                )
            else:
                ok_rows.append(item)

        payload = {
            "ready": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "since_utc": since.isoformat(),
            "checked": len(rows),
            "inconsistent_count": len(inconsistent),
            "ok_count": len(ok_rows),
            "inconsistent": inconsistent,
            "ok": len(inconsistent) == 0,
        }
        print(json.dumps(payload, indent=2, default=str))
        return 1 if inconsistent else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
