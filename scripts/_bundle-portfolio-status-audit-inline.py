"""Audit prod — statut bundle portfolio + lock metadata (lecture seule)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from database import SessionLocal

PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"
PORTFOLIO_ID = "ab4ae920-f3e8-481b-8f82-a41a81d5779d"
BATCH_PREFIX = os.environ.get("BATCH_PREFIX", "")


def main() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
    db = SessionLocal()
    try:
        portfolio = db.execute(
            text(
                """
                SELECT id::text, name, metadata::text AS metadata_raw
                FROM pe_portfolios
                WHERE id = :pid
                """
            ),
            {"pid": PORTFOLIO_ID},
        ).mappings().first()

        meta = {}
        if portfolio and portfolio.get("metadata_raw"):
            meta = json.loads(portfolio["metadata_raw"])

        parents = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, status, created_at, updated_at,
                           metadata_json->>'batch_id' AS batch_id,
                           metadata_json->'legs' AS legs
                    FROM transaction_intents
                    WHERE person_id = :person
                      AND product_type = 'bundle_invest'
                      AND created_at >= :cutoff
                    ORDER BY created_at DESC
                    LIMIT 15
                    """
                ),
                {"person": PERSON_ID, "cutoff": cutoff},
            )
        ]

        swap_filter = ""
        swap_params: dict = {"person": PERSON_ID, "cutoff": cutoff}
        if BATCH_PREFIX:
            swap_filter = "AND elem->>'batch_id' LIKE :batch_prefix"
            swap_params["batch_prefix"] = f"{BATCH_PREFIX}%"

        swaps = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    f"""
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
                    WHERE s.person_id = :person
                      AND s.created_at >= :cutoff
                      AND EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                        WHERE elem->>'event' = 'bundle_leg_context'
                          AND COALESCE(elem->>'bundle_execution', 'false') = 'true'
                          {swap_filter}
                      )
                    ORDER BY s.created_at DESC
                    LIMIT 30
                    """
                ),
                swap_params,
            )
        ]

        out = {
            "phase": "bundle_portfolio_status_audit",
            "portfolio_id": PORTFOLIO_ID,
            "portfolio_name": portfolio.get("name") if portfolio else None,
            "bundle_invest_lock": meta.get("bundle_invest_lock"),
            "parents_matching": parents,
            "swaps_for_batch_prefix": swaps,
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
