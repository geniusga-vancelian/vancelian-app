"""Forensic swap c05f5709 — prepare_execute vs quote_refreshed (SQL only)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from database import SessionLocal
from sqlalchemy import text

SWAP_ID = "c05f5709-0c32-4db8-b8b8-fe89ebe4931c"
PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"


def main() -> None:
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT id::text, status, from_asset, to_asset,
                       amount_in::text, estimated_receive::text,
                       expires_at::text, error_message, tx_hash,
                       created_at::text, updated_at::text,
                       audit_log, transaction_request
                FROM person_wallet_swaps
                WHERE id = :sid AND person_id = :pid
                """
            ),
            {"sid": SWAP_ID, "pid": PERSON_ID},
        ).mappings().first()

        if row is None:
            print(json.dumps({"error": "swap_not_found"}, indent=2))
            return

        audit = row["audit_log"] if isinstance(row["audit_log"], list) else []
        events = [e for e in audit if isinstance(e, dict)]
        tx_req = row["transaction_request"] if isinstance(row["transaction_request"], dict) else {}

        intent = db.execute(
            text(
                """
                SELECT id::text, status, product_type, metadata_json
                FROM transaction_intents
                WHERE linked_table = 'person_wallet_swaps'
                  AND linked_id = :sid
                LIMIT 1
                """
            ),
            {"sid": SWAP_ID},
        ).mappings().first()

        report = {
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "swap_id": row["id"],
            "status": row["status"],
            "from_asset": row["from_asset"],
            "to_asset": row["to_asset"],
            "amount_in": row["amount_in"],
            "estimated_receive": row["estimated_receive"],
            "expires_at": row["expires_at"],
            "error_message": row["error_message"],
            "tx_hash": row["tx_hash"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "transaction_request_present": bool(tx_req.get("to")),
            "linked_intent": dict(intent) if intent else None,
            "audit_event_names": [e.get("event") for e in events],
            "has_awaiting_signature": any(e.get("event") == "awaiting_signature" for e in events),
            "has_quote_refreshed": any(e.get("event") == "quote_refreshed" for e in events),
            "has_execution_failed": any(e.get("event") == "execution_failed" for e in events),
            "has_wallet_locked": any(e.get("event") == "wallet_locked" for e in events),
            "key_events": [
                {
                    "at": e.get("at"),
                    "event": e.get("event"),
                    "step": e.get("step"),
                    "reason": e.get("reason"),
                    "detail": e.get("detail"),
                    "code": e.get("code"),
                }
                for e in events
                if e.get("event")
                in (
                    "bundle_quote_received",
                    "quote_refreshed",
                    "quote_refresh_failed",
                    "awaiting_signature",
                    "wallet_locked",
                    "submitted",
                    "auto_expired",
                    "execution_failed",
                    "client_trace",
                    "confirm_prepare_failed",
                )
            ],
            "full_audit": events,
        }

        print(json.dumps(report, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
