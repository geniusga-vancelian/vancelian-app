"""Lombard scope movements — dry-run from OVT legacy + metadata."""
from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from .enums import InternalMovementType, InternalScope
from .types import ScopeMovement, ScopeMovementSet
from .utils import (
    LOMBARD_INTEGRATION_MODE,
    accumulate_movement_net,
    borrow_usdc_from_metadata,
    collateral_quantity_from_metadata,
    collateral_symbol_from_metadata,
    normalize_asset,
    ovt_table_exists,
    parse_metadata,
)


def compute_expected_lombard_scope_movements(
    db: Session,
    person_id: UUID,
    *,
    limit: int = 200,
) -> ScopeMovementSet:
    """
    Dérive les mouvements attendus depuis OVT Lombard success (open_loan).

    collateral lock : trading_available − / trading_locked_collateral +
    borrow USDC     : trading_available + / liability +
    """
    result = ScopeMovementSet(person_id=person_id, product="lombard")
    if not ovt_table_exists(db):
        result.notes.append("Table onchain_vault_transactions absente.")
        return result

    rows = db.execute(
        sa.text(
            """
            SELECT id, operation, status, amount_raw, asset_symbol, asset_decimals,
                   metadata_json, tx_hash, group_key, created_at
            FROM onchain_vault_transactions
            WHERE person_id = :person_id
              AND integration_mode = :mode
              AND status = 'success'
            ORDER BY created_at ASC
            LIMIT :limit
            """
        ),
        {
            "person_id": str(person_id),
            "mode": LOMBARD_INTEGRATION_MODE,
            "limit": limit,
        },
    ).mappings().all()

    open_loan_rows = []
    for row in rows:
        meta = parse_metadata(row.get("metadata_json"))
        op = str(row["operation"] or "").strip().lower()
        lombard_op = str(meta.get("lombard_operation") or "").strip().lower()
        if lombard_op == "open_loan" or (op == "deposit" and lombard_op != "repay"):
            if op == "deposit" or lombard_op == "open_loan":
                open_loan_rows.append((row, meta))

    seen_groups: set[str] = set()
    for row, meta in open_loan_rows:
        group_key = str(row.get("group_key") or row["id"])
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)

        ovt_id = str(row["id"])
        collateral_asset = collateral_symbol_from_metadata(meta)
        collateral_parse = collateral_quantity_from_metadata(meta, asset=collateral_asset)
        if collateral_parse.warnings:
            result.notes.extend(collateral_parse.warnings)
        if collateral_parse.missing_decimals:
            result.collateral_parse_issues.append(
                {
                    "gap_type": "missing_decimals_gap",
                    "asset": collateral_asset or "UNKNOWN",
                    "reference_id": ovt_id,
                    "group_key": group_key,
                    "guarantee_amount_raw": meta.get("guarantee_amount_raw"),
                    "message": collateral_parse.warnings[0] if collateral_parse.warnings else "",
                }
            )
        collateral_qty = collateral_parse.quantity
        borrow_qty = borrow_usdc_from_metadata(
            meta,
            fallback_decimals=int(row["asset_decimals"] or 6),
        )

        if collateral_asset and collateral_qty and collateral_qty > 0:
            lock = ScopeMovement(
                movement_type=InternalMovementType.LOCK.value,
                source_scope=InternalScope.TRADING_AVAILABLE.value,
                destination_scope=InternalScope.TRADING_LOCKED_COLLATERAL.value,
                asset=collateral_asset,
                quantity=collateral_qty,
                reference_id=ovt_id,
                source_system="onchain_vault_transactions",
                metadata={
                    "group_key": group_key,
                    "lombard_operation": "open_loan",
                    "tx_hash": row["tx_hash"],
                    **(
                        {
                            "collateral_decimals": collateral_parse.decimals,
                            "collateral_decimals_source": collateral_parse.decimals_source,
                        }
                        if collateral_parse.decimals is not None
                        else {}
                    ),
                },
            )
            result.movements.append(lock)
            accumulate_movement_net(result.net_by_scope, lock)

        if borrow_qty and borrow_qty > 0:
            borrow = ScopeMovement(
                movement_type=InternalMovementType.BORROW.value,
                source_scope=InternalScope.LIABILITY.value,
                destination_scope=InternalScope.TRADING_AVAILABLE.value,
                asset="USDC",
                quantity=borrow_qty,
                reference_id=ovt_id,
                source_system="onchain_vault_transactions",
                metadata={
                    "group_key": group_key,
                    "lombard_operation": "open_loan",
                    "tx_hash": row["tx_hash"],
                    "movement_semantics": "liability_credit_and_trading_available_credit",
                },
            )
            result.movements.append(borrow)
            from .utils import apply_net_delta

            apply_net_delta(
                result.net_by_scope,
                scope=InternalScope.LIABILITY.value,
                asset="USDC",
                delta=borrow_qty,
            )
            apply_net_delta(
                result.net_by_scope,
                scope=InternalScope.TRADING_AVAILABLE.value,
                asset="USDC",
                delta=borrow_qty,
            )

    if not result.movements:
        result.notes.append("Aucun open_loan Lombard success détecté pour cette personne.")

    return result
