"""Vault scope movements — dry-run from OVT legacy (Morpho / Ledgity)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from .enums import InternalMovementType, InternalScope
from .types import ScopeMovement, ScopeMovementSet
from .utils import (
    VAULT_INTEGRATION_MODES,
    accumulate_movement_net,
    normalize_asset,
    ovt_table_exists,
    parse_raw_amount,
)


def compute_expected_vault_scope_movements(
    db: Session,
    person_id: UUID,
    *,
    limit: int = 500,
) -> ScopeMovementSet:
    """
    Dérive les mouvements de scope attendus depuis les OVT vault success.

    deposit success → trading_available − / vault_position +
    withdraw success → vault_position − / trading_available +
    """
    result = ScopeMovementSet(person_id=person_id, product="vault")
    if not ovt_table_exists(db):
        result.notes.append("Table onchain_vault_transactions absente.")
        return result

    rows = db.execute(
        sa.text(
            """
            SELECT id, operation, status, amount_raw, asset_symbol, asset_decimals,
                   integration_mode, tx_hash, created_at
            FROM onchain_vault_transactions
            WHERE person_id = :person_id
              AND integration_mode = ANY(:modes)
              AND status = 'success'
              AND operation::text IN ('deposit', 'withdraw')
            ORDER BY created_at ASC
            LIMIT :limit
            """
        ),
        {
            "person_id": str(person_id),
            "modes": list(VAULT_INTEGRATION_MODES),
            "limit": limit,
        },
    ).mappings().all()

    for row in rows:
        operation = str(row["operation"] or "").strip().lower()
        asset = normalize_asset(row["asset_symbol"])
        qty = parse_raw_amount(str(row["amount_raw"]), int(row["asset_decimals"] or 6))
        if qty <= 0:
            continue

        ovt_id = str(row["id"])
        if operation == "deposit":
            movement = ScopeMovement(
                movement_type=InternalMovementType.FUND.value,
                source_scope=InternalScope.TRADING_AVAILABLE.value,
                destination_scope=InternalScope.VAULT_POSITION.value,
                asset=asset,
                quantity=qty,
                reference_id=ovt_id,
                source_system="onchain_vault_transactions",
                metadata={
                    "integration_mode": row["integration_mode"],
                    "tx_hash": row["tx_hash"],
                    "operation": operation,
                },
            )
        elif operation == "withdraw":
            movement = ScopeMovement(
                movement_type=InternalMovementType.RELEASE.value,
                source_scope=InternalScope.VAULT_POSITION.value,
                destination_scope=InternalScope.TRADING_AVAILABLE.value,
                asset=asset,
                quantity=qty,
                reference_id=ovt_id,
                source_system="onchain_vault_transactions",
                metadata={
                    "integration_mode": row["integration_mode"],
                    "tx_hash": row["tx_hash"],
                    "operation": operation,
                },
            )
        else:
            continue

        result.movements.append(movement)
        accumulate_movement_net(result.net_by_scope, movement)

    if not result.movements:
        result.notes.append("Aucun OVT vault deposit/withdraw success pour cette personne.")

    return result
