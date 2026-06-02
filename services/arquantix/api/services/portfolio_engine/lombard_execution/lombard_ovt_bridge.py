"""Bridge OVT Lombard open_loan success → scope movements PE (Phase 3B)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.portfolio_engine.internal_scope_movements.utils import (
    LOMBARD_INTEGRATION_MODE,
    borrow_usdc_from_metadata,
    collateral_quantity_from_metadata,
    collateral_symbol_from_metadata,
    parse_metadata,
    resolve_client_id,
)
from services.portfolio_engine.direct_overlay import _resolve_or_create_instrument
from services.portfolio_engine.lombard_execution.lombard_funding import (
    LombardFundingError,
    open_lombard_loan,
)

LOMBARD_INTEGRATION = LOMBARD_INTEGRATION_MODE


def _is_lombard_open_loan_row(row: sa.RowMapping, meta: dict[str, Any]) -> bool:
    mode = str(row.get("integration_mode") or LOMBARD_INTEGRATION).strip().lower()
    if mode != LOMBARD_INTEGRATION:
        return False
    if str(row.get("status") or "").strip().lower() != "success":
        return False
    op = str(row.get("operation") or "").strip().lower()
    lombard_op = str(meta.get("lombard_operation") or "").strip().lower()
    if lombard_op == "repay":
        return False
    if op in ("approve", "authorize"):
        return False
    return lombard_op == "open_loan" or (op == "deposit" and lombard_op != "repay")


def apply_lombard_scope_movement_for_ovt(
    db: Session,
    *,
    ovt_id: str,
    person_id: UUID,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Applique lock + borrow Lombard pour un OVT open_loan success (idempotent via ovt_id)."""
    row = db.execute(
        sa.text(
            """
            SELECT id, operation, status, amount_raw, asset_symbol, asset_decimals,
                   integration_mode, tx_hash, person_id, group_key, metadata_json
            FROM onchain_vault_transactions
            WHERE id = :ovt_id AND person_id = :person_id
            """
        ),
        {"ovt_id": ovt_id, "person_id": str(person_id)},
    ).mappings().first()

    if row is None:
        return {"ok": False, "reason": "ovt_not_found", "ovt_id": ovt_id}

    meta = parse_metadata(row.get("metadata_json"))
    if not _is_lombard_open_loan_row(row, meta):
        return {"ok": False, "reason": "not_lombard_open_loan", "ovt_id": ovt_id}

    client_id = resolve_client_id(db, person_id)
    if client_id is None:
        return {"ok": False, "reason": "client_not_found", "ovt_id": ovt_id}

    collateral_asset = collateral_symbol_from_metadata(meta)
    collateral_parse = collateral_quantity_from_metadata(meta, asset=collateral_asset)
    collateral_qty = collateral_parse.quantity or Decimal("0")
    borrow_qty = borrow_usdc_from_metadata(
        meta,
        fallback_decimals=int(row["asset_decimals"] or 6),
    ) or Decimal("0")

    if collateral_parse.missing_decimals and collateral_asset:
        return {
            "ok": False,
            "reason": "lombard.lock.missing_decimals",
            "ovt_id": ovt_id,
            "message": collateral_parse.warnings[0] if collateral_parse.warnings else "",
            "collateral_asset": collateral_asset,
        }

    if collateral_qty <= 0 and borrow_qty <= 0:
        return {"ok": False, "reason": "zero_amounts", "ovt_id": ovt_id}

    collateral_instrument_id = None
    if collateral_asset and collateral_qty > 0:
        collateral_instrument_id = _resolve_or_create_instrument(db, collateral_asset).id

    payload: dict[str, Any] = {
        "ovt_id": ovt_id,
        "person_id": str(person_id),
        "client_id": str(client_id),
        "collateral_asset": collateral_asset,
        "collateral_amount": str(collateral_qty),
        "borrow_amount": str(borrow_qty),
        "integration_mode": row["integration_mode"],
        "tx_hash": row["tx_hash"],
        "group_key": row.get("group_key"),
        "dry_run": dry_run,
    }

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_apply": "open_lombard_loan",
            **payload,
        }

    if collateral_qty > 0 and collateral_instrument_id is None:
        return {"ok": False, "reason": "collateral_asset_unresolved", **payload}

    try:
        result = open_lombard_loan(
            db,
            client_id=client_id,
            person_id=person_id,
            collateral_asset=collateral_asset or "",
            collateral_instrument_id=collateral_instrument_id or _resolve_or_create_instrument(db, "USDC").id,
            collateral_amount=collateral_qty if collateral_qty > 0 else Decimal("0"),
            borrow_amount=borrow_qty,
            linked_reference_id=ovt_id,
            integration_mode=str(row["integration_mode"] or LOMBARD_INTEGRATION),
            tx_hash=row["tx_hash"],
            group_key=str(row.get("group_key") or ""),
        )
    except LombardFundingError as exc:
        return {"ok": False, "reason": exc.code, "message": str(exc), **payload}

    return {"ok": True, "dry_run": False, "result": result, **payload}


def plan_lombard_scope_backfill_for_person(
    db: Session,
    *,
    person_id: UUID,
    limit: int = 200,
) -> dict[str, Any]:
    """Liste les OVT Lombard open_loan success à rejouer (dry-run migration plan)."""
    rows = db.execute(
        sa.text(
            """
            SELECT id, operation, status, amount_raw, asset_symbol, asset_decimals,
                   integration_mode, metadata_json, tx_hash, group_key, created_at
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
            "mode": LOMBARD_INTEGRATION,
            "limit": limit,
        },
    ).mappings().all()

    planned = []
    for row in rows:
        meta = parse_metadata(row.get("metadata_json"))
        if not _is_lombard_open_loan_row(row, meta):
            continue
        preview = apply_lombard_scope_movement_for_ovt(
            db,
            ovt_id=str(row["id"]),
            person_id=person_id,
            dry_run=True,
        )
        planned.append(preview)

    return {
        "person_id": str(person_id),
        "dry_run": True,
        "ovt_count": len(planned),
        "planned_movements": planned,
    }
