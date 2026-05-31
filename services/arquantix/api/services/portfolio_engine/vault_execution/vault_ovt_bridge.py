"""Bridge OVT vault success → scope movements PE (Phase 3A / 3A+1a).

Branché live depuis ``dual_write_vault_step`` après receipt OVT success
(Morpho / Ledgity deposit & withdraw uniquement).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.portfolio_engine.internal_scope_movements.utils import (
    VAULT_INTEGRATION_MODES,
    parse_raw_amount,
    resolve_client_id,
)
from services.portfolio_engine.direct_overlay import _resolve_or_create_instrument
from services.portfolio_engine.vault_execution.vault_funding import (
    VaultFundingError,
    fund_vault_from_self_trading,
    release_vault_to_self_trading,
)

VAULT_OPERATIONS_FUND = frozenset({"deposit"})
VAULT_OPERATIONS_RELEASE = frozenset({"withdraw"})


def apply_vault_scope_movement_for_ovt(
    db: Session,
    *,
    ovt_id: str,
    person_id: UUID,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Applique fund/release vault pour un OVT success (idempotent via linked_reference_id)."""
    row = db.execute(
        sa.text(
            """
            SELECT id, operation, status, amount_raw, asset_symbol, asset_decimals,
                   integration_mode, tx_hash, person_id
            FROM onchain_vault_transactions
            WHERE id = :ovt_id AND person_id = :person_id
            """
        ),
        {"ovt_id": ovt_id, "person_id": str(person_id)},
    ).mappings().first()

    if row is None:
        return {"ok": False, "reason": "ovt_not_found", "ovt_id": ovt_id}

    if str(row["status"] or "").lower() != "success":
        return {"ok": False, "reason": "ovt_not_success", "ovt_id": ovt_id, "status": row["status"]}

    mode = str(row["integration_mode"] or "").strip().lower()
    if mode not in VAULT_INTEGRATION_MODES:
        return {"ok": False, "reason": "not_vault_integration", "ovt_id": ovt_id, "integration_mode": mode}

    operation = str(row["operation"] or "").strip().lower()
    if operation not in VAULT_OPERATIONS_FUND | VAULT_OPERATIONS_RELEASE:
        return {"ok": False, "reason": "unsupported_operation", "ovt_id": ovt_id, "operation": operation}

    client_id = resolve_client_id(db, person_id)
    if client_id is None:
        return {"ok": False, "reason": "client_not_found", "ovt_id": ovt_id}

    asset = str(row["asset_symbol"] or "USDC").upper()
    amount = parse_raw_amount(
        str(row["amount_raw"]),
        int(row["asset_decimals"] or 6),
    )
    if amount <= 0:
        return {"ok": False, "reason": "zero_amount", "ovt_id": ovt_id}

    instrument = _resolve_or_create_instrument(db, asset)
    payload = {
        "ovt_id": ovt_id,
        "person_id": str(person_id),
        "client_id": str(client_id),
        "operation": operation,
        "asset": asset,
        "amount": str(amount),
        "integration_mode": mode,
        "tx_hash": row["tx_hash"],
        "dry_run": dry_run,
    }

    if dry_run:
        action = "fund_vault_from_self_trading" if operation in VAULT_OPERATIONS_FUND else "release_vault_to_self_trading"
        return {"ok": True, "dry_run": True, "would_apply": action, **payload}

    try:
        if operation in VAULT_OPERATIONS_FUND:
            result = fund_vault_from_self_trading(
                db,
                client_id=client_id,
                person_id=person_id,
                asset=asset,
                instrument_id=instrument.id,
                amount=amount,
                linked_reference_id=ovt_id,
                integration_mode=mode,
                tx_hash=row["tx_hash"],
            )
        else:
            result = release_vault_to_self_trading(
                db,
                client_id=client_id,
                person_id=person_id,
                asset=asset,
                instrument_id=instrument.id,
                amount=amount,
                linked_reference_id=ovt_id,
                integration_mode=mode,
                tx_hash=row["tx_hash"],
            )
    except VaultFundingError as exc:
        return {"ok": False, "reason": exc.code, "message": str(exc), **payload}

    return {"ok": True, "dry_run": False, "result": result, **payload}


def plan_vault_scope_backfill_for_person(
    db: Session,
    *,
    person_id: UUID,
    limit: int = 500,
) -> dict[str, Any]:
    """Liste les OVT vault success à rejouer (dry-run migration plan)."""
    rows = db.execute(
        sa.text(
            """
            SELECT id, operation, status, amount_raw, asset_symbol, asset_decimals,
                   integration_mode, tx_hash, created_at
            FROM onchain_vault_transactions
            WHERE person_id = :person_id
              AND integration_mode IN :modes
              AND status = 'success'
              AND operation IN ('deposit', 'withdraw')
            ORDER BY created_at ASC
            LIMIT :limit
            """
        ),
        {
            "person_id": str(person_id),
            "modes": tuple(VAULT_INTEGRATION_MODES),
            "limit": limit,
        },
    ).mappings().all()

    planned = []
    for row in rows:
        preview = apply_vault_scope_movement_for_ovt(
            db,
            ovt_id=str(row["id"]),
            person_id=person_id,
            dry_run=True,
        )
        planned.append(preview)

    fund_count = sum(1 for p in planned if p.get("operation") == "deposit")
    release_count = sum(1 for p in planned if p.get("operation") == "withdraw")
    return {
        "person_id": str(person_id),
        "dry_run": True,
        "ovt_count": len(planned),
        "fund_count": fund_count,
        "release_count": release_count,
        "planned_movements": planned,
    }
