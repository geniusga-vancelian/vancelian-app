"""Audit read-only — dépôt +20 USDC Two Crypto Kings sans allocation visible."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from database import SessionLocal

PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"
CLIENT_ID = "080358a8-4519-4acf-b5da-25485446c967"
PORTFOLIO_ID = "daea3720-e58e-410f-a796-3bbd541ac608"
PORTFOLIO_NAME = "Two Crypto Kings"
TARGET_AMOUNT = Decimal("20")


def _chain_step(exists: bool, **kwargs: Any) -> dict[str, Any]:
    return {"exists": exists, **kwargs}


def _ui_panel_would_show(*, cash_leg: float, spot_notional: float, lock_active: bool) -> dict[str, Any]:
    has_unallocated_cash = cash_leg > 1.0 and spot_notional < (cash_leg * 0.25)
    panel_visible = has_unallocated_cash or lock_active
    return {
        "cash_leg_display_value": cash_leg,
        "spot_notional_estimate": spot_notional,
        "has_unallocated_cash_rule": has_unallocated_cash,
        "lock_active": lock_active,
        "allocation_panel_visible": panel_visible,
        "invest_in_progress_banner": lock_active,
        "resume_button": lock_active,
    }


def main() -> None:
    audit_iso = datetime.now(timezone.utc).isoformat()
    db = SessionLocal()
    try:
        # --- Latest +20 USDC deposit (ledger) ---
        latest_ledger_deposit = db.execute(
            text(
                """
                SELECT id::text, batch_id, quantity::text, created_at, source_id,
                       event_type, metadata::text AS metadata_raw
                FROM bundle_ledger_entries
                WHERE person_id = :pid
                  AND bundle_portfolio_id = :portfolio
                  AND event_type = 'BUNDLE_DEPOSIT'
                  AND UPPER(asset_symbol) = 'USDC'
                  AND quantity >= 19.5 AND quantity <= 20.5
                ORDER BY created_at DESC
                LIMIT 5
                """
            ),
            {"pid": PERSON_ID, "portfolio": PORTFOLIO_ID},
        ).mappings().all()

        latest_audit_fund = db.execute(
            text(
                """
                SELECT id::text, created_at, metadata::text AS metadata_raw
                FROM pe_audit_events
                WHERE action = 'bundle.fund_cash_leg'
                  AND entity_id = :portfolio
                ORDER BY created_at DESC
                LIMIT 10
                """
            ),
            {"portfolio": PORTFOLIO_ID},
        ).mappings().all()

        # Pick primary deposit trace
        deposit_batch_id = None
        deposit_ts = None
        deposit_ledger_id = None
        if latest_ledger_deposit:
            row = latest_ledger_deposit[0]
            deposit_batch_id = row["batch_id"]
            deposit_ts = str(row["created_at"])
            deposit_ledger_id = row["id"]

        # Match audit fund for same batch
        audit_fund_match = None
        for row in latest_audit_fund:
            meta = json.loads(row["metadata_raw"] or "{}")
            bid = str(meta.get("batch_id") or "")
            amt = Decimal(str(meta.get("amount") or "0"))
            if deposit_batch_id and bid == deposit_batch_id:
                audit_fund_match = {"audit_id": row["id"], "created_at": str(row["created_at"]), "meta": meta}
                break
            if 19.5 <= float(amt) <= 20.5 and audit_fund_match is None:
                audit_fund_match = {"audit_id": row["id"], "created_at": str(row["created_at"]), "meta": meta}
                if not deposit_batch_id:
                    deposit_batch_id = bid
                    deposit_ts = str(row["created_at"])

        batch_id = deposit_batch_id

        # Portfolio metadata + cash leg
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

        portfolio_meta = json.loads(portfolio["metadata_raw"] or "{}") if portfolio else {}
        invest_lock = portfolio_meta.get("bundle_invest_lock")

        cash_leg = db.execute(
            text(
                """
                SELECT pa.id::text, pa.quantity::text, a.symbol
                FROM pe_position_atoms pa
                JOIN pe_instruments i ON i.id = pa.instrument_id
                JOIN pe_assets a ON a.id = i.asset_id
                WHERE pa.portfolio_id = :portfolio
                  AND pa.position_type = 'cash'
                  AND pa.status = 'open'
                  AND UPPER(a.symbol) IN ('USDC', 'USDC.E')
                ORDER BY pa.updated_at DESC
                LIMIT 3
                """
            ),
            {"portfolio": PORTFOLIO_ID},
        ).mappings().all()

        spot_positions = db.execute(
            text(
                """
                SELECT pa.quantity::text, a.symbol, pa.market_value::text, pa.cost_basis::text
                FROM pe_position_atoms pa
                JOIN pe_instruments i ON i.id = pa.instrument_id
                JOIN pe_assets a ON a.id = i.asset_id
                WHERE pa.portfolio_id = :portfolio
                  AND pa.position_type = 'spot'
                  AND pa.status = 'open'
                  AND pa.quantity > 0
                """
            ),
            {"portfolio": PORTFOLIO_ID},
        ).mappings().all()

        spot_notional = 0.0
        for sp in spot_positions:
            for field in ("market_value", "cost_basis"):
                raw = sp.get(field)
                if raw is not None:
                    try:
                        spot_notional += float(raw)
                        break
                    except (TypeError, ValueError):
                        pass

        cash_leg_qty = float(cash_leg[0]["quantity"]) if cash_leg else 0.0

        # Parent intent
        parent = None
        if batch_id:
            parent = db.execute(
                text(
                    """
                    SELECT id::text, status, created_at, updated_at,
                           metadata_json->>'batch_id' AS batch_id,
                           metadata_json->>'portfolio_id' AS portfolio_id,
                           metadata_json->'legs' AS legs,
                           metadata_json->>'funding_amount' AS funding_amount,
                           metadata_json->>'phase' AS phase,
                           metadata_json->>'plan_hash' AS plan_hash,
                           metadata_json->>'planner_version' AS planner_version,
                           parent_intent_id::text
                    FROM transaction_intents
                    WHERE person_id = :pid
                      AND product_type = 'bundle_invest'
                      AND metadata_json->>'batch_id' = :batch
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"pid": PERSON_ID, "batch": batch_id},
            ).mappings().first()

        children = []
        if parent and parent.get("id"):
            children = [
                dict(r._mapping)
                for r in db.execute(
                    text(
                        """
                        SELECT id::text, status, product_type, operation_type,
                               linked_table, linked_id::text, created_at,
                               metadata_json->>'leg_index' AS leg_index
                        FROM transaction_intents
                        WHERE parent_intent_id = :parent
                        ORDER BY created_at ASC
                        """
                    ),
                    {"parent": parent["id"]},
                )
            ]

        swaps = []
        if batch_id:
            swaps = [
                dict(r._mapping)
                for r in db.execute(
                    text(
                        """
                        SELECT s.id::text, s.status, s.from_asset, s.to_asset, s.amount_in::text,
                               s.tx_hash, s.created_at, s.confirmed_at,
                               (SELECT elem->>'leg_id'
                                FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                                WHERE elem->>'event' = 'bundle_leg_context'
                                LIMIT 1) AS leg_id
                        FROM person_wallet_swaps s
                        WHERE s.person_id = :pid
                          AND EXISTS (
                            SELECT 1
                            FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb, '[]'::jsonb)) elem
                            WHERE elem->>'event' = 'bundle_leg_context'
                              AND elem->>'batch_id' = :batch
                          )
                        ORDER BY s.created_at ASC
                        """
                    ),
                    {"pid": PERSON_ID, "batch": batch_id},
                )
            ]

        # Ledger entries for batch (activity feed source)
        ledger_batch = []
        if batch_id:
            ledger_batch = [
                dict(r._mapping)
                for r in db.execute(
                    text(
                        """
                        SELECT id::text, event_type, quantity::text, created_at, source_id
                        FROM bundle_ledger_entries
                        WHERE batch_id = :batch
                        ORDER BY created_at ASC
                        """
                    ),
                    {"batch": batch_id},
                )
            ]

        # All recent +20 deposits on portfolio for cash attribution
        deposits_all = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT batch_id, quantity::text, created_at, event_type
                    FROM bundle_ledger_entries
                    WHERE bundle_portfolio_id = :portfolio
                      AND person_id = :pid
                      AND event_type = 'BUNDLE_DEPOSIT'
                    ORDER BY created_at ASC
                    """
                ),
                {"portfolio": PORTFOLIO_ID, "pid": PERSON_ID},
            )
        ]

        allocations_confirmed = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT batch_id, quantity::text, asset_symbol, created_at
                    FROM bundle_ledger_entries
                    WHERE bundle_portfolio_id = :portfolio
                      AND person_id = :pid
                      AND event_type = 'BUNDLE_ALLOCATION_BUY'
                    ORDER BY created_at ASC
                    """
                ),
                {"portfolio": PORTFOLIO_ID, "pid": PERSON_ID},
            )
        ]

        lock_status = str((invest_lock or {}).get("status") or "")
        lock_batch = str((invest_lock or {}).get("batch_id") or "")
        lock_active_statuses = {
            "pending_signature", "signature_requested", "submitted",
            "pending_confirmation", "finalizing", "partial_pending",
        }
        lock_active = bool(invest_lock and lock_status in lock_active_statuses)

        ui_sim = _ui_panel_would_show(
            cash_leg=cash_leg_qty,
            spot_notional=spot_notional,
            lock_active=lock_active,
        )

        # Orphan chain
        chain = {
            "deposit_ledger": _chain_step(
                bool(latest_ledger_deposit),
                ledger_id=deposit_ledger_id,
                batch_id=batch_id,
                timestamp=deposit_ts,
            ),
            "audit_fund": _chain_step(
                audit_fund_match is not None,
                **(audit_fund_match or {}),
            ),
            "batch_id": _chain_step(bool(batch_id), batch_id=batch_id),
            "parent_intent": _chain_step(
                parent is not None,
                intent_id=(parent or {}).get("id"),
                status=(parent or {}).get("status"),
                timestamp=str((parent or {}).get("created_at")) if parent else None,
            ),
            "child_intents": _chain_step(len(children) > 0, count=len(children), items=children),
            "swaps": _chain_step(len(swaps) > 0, count=len(swaps), items=swaps),
            "ledger_allocation_rows": _chain_step(
                any(e["event_type"] == "BUNDLE_ALLOCATION_BUY" for e in ledger_batch),
                events=[e["event_type"] for e in ledger_batch],
            ),
        }

        # Classification
        classification = "UNKNOWN"
        root_cause = ""
        repair = ""

        if not batch_id and latest_ledger_deposit:
            classification = "ORPHAN_DEPOSIT"
            root_cause = "Dépôt ledger sans batch_id traçable."
            repair = "Audit manuel pe_audit_events + PE transfer; pas de reprise auto."
        elif batch_id and parent is None:
            classification = "ORPHAN_BATCH"
            root_cause = "Funding/batch_id présent mais parent intent bundle_invest absent."
            repair = "Créer/lier parent via recovery contrôlée (hors scope auto)."
        elif parent and not swaps and not children:
            classification = "ORPHAN_PARENT"
            root_cause = "Parent créé mais aucun swap/child — orchestration arrêtée après funding."
            repair = "Resume invest ou recovery batch via UI/API legacy."
        elif swaps and not any(e["event_type"] == "BUNDLE_ALLOCATION_BUY" for e in ledger_batch):
            if not lock_active and not ui_sim["allocation_panel_visible"]:
                classification = "PARTIAL_BATCH_HIDDEN"
                root_cause = (
                    "Swaps créés (souvent AWAITING_SIGNATURE) mais pas d'allocation ledger confirmée; "
                    "lock portfolio absent ou réconcilié; panneau UI masqué (spot_notional vs cash rule)."
                )
                repair = "Reprise manuelle swaps pending; corriger UI gate hasUnallocatedCash + lock reconcile."
            else:
                classification = "ORPHAN_SWAP"
                root_cause = "Swaps existent mais non confirmés — pas de ligne allocation activity."
                repair = "Signer legs LI.FI via reprise invest."
        elif lock_batch and batch_id and lock_batch != batch_id:
            classification = "UI_RENDERING_BUG"
            root_cause = f"Lock portfolio pointe batch {lock_batch[:8]}… ≠ dépôt {batch_id[:8]}…"
            repair = "Aligner lock metadata sur batch actif ou recovery."
        elif not lock_active and not ui_sim["allocation_panel_visible"] and batch_id:
            classification = "PARTIAL_BATCH_HIDDEN"
            root_cause = (
                "Batch partiel en DB mais UI masquée: reconcile_or_expire_idle_invest_lock a probablement "
                "cleared le lock, et hasUnallocatedCash=false car positions spot présentes."
            )
            repair = "Exposer reprise si swaps pending même sans lock; ne pas clear lock si AWAITING_SIGNATURE."
        elif parent and str(parent.get("status")) in {"partial", "awaiting_signature", "submitted"}:
            classification = "PARTIAL_BATCH_HIDDEN"
            root_cause = "Batch partiel actif en DB; UI ne montre ni lock ni reprise."
            repair = "Vérifier active-lock reconcile + règle hasUnallocatedCash."

        out = {
            "phase": "missing_allocation_after_bundle_deposit_audit",
            "audit_iso": audit_iso,
            "person_id": PERSON_ID,
            "client_id": CLIENT_ID,
            "portfolio_id": PORTFOLIO_ID,
            "portfolio_name": PORTFOLIO_NAME,
            "target_deposit_usdc": str(TARGET_AMOUNT),
            "latest_deposit": {
                "ledger_rows": [dict(r) for r in latest_ledger_deposit],
                "audit_fund_match": audit_fund_match,
                "resolved_batch_id": batch_id,
            },
            "chain": chain,
            "portfolio_metadata": {
                "bundle_invest_lock": invest_lock,
                "lock_points_to_same_batch": lock_batch == (batch_id or ""),
            },
            "parent_intent": dict(parent) if parent else None,
            "cash_leg": [dict(c) for c in cash_leg],
            "spot_positions": [dict(s) for s in spot_positions],
            "cash_attribution": {
                "cash_leg_usdc_now": cash_leg_qty,
                "historical_deposits": deposits_all,
                "confirmed_allocations": allocations_confirmed,
                "note": "cash élevé = cumul dépôts non alloués + legs non confirmés + reliquats",
            },
            "activity_feed_analysis": {
                "deposit_visible_reason": "bundle_ledger BUNDLE_DEPOSIT toujours projeté",
                "allocation_missing_reason": (
                    "BUNDLE_ALLOCATION_BUY écrit à confirmation swap — "
                    "pas de ligne si legs AWAITING_SIGNATURE/SUBMITTED non confirmés"
                ),
                "ledger_events_for_batch": ledger_batch,
            },
            "ui_state_simulation": ui_sim,
            "classification": classification,
            "root_cause": root_cause,
            "recommended_repair_action": repair,
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
