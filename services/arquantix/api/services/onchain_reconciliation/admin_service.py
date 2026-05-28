"""Logique admin réconciliation on-chain (Phase 5A — pas d'apply destructif)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.repository import RawOnChainEventRepository

from .correction_service import (
    assert_no_destructive_apply,
    correction_to_dict,
    record_correction_request,
)
from .discrepancy_models import ReconciliationCorrection, ReconciliationDiscrepancy
from .discrepancy_repository import DiscrepancyRepository, discrepancy_to_dict
from .discrepancy_insights import enrich_discrepancy_dict
from .preview_service import build_correction_preview, resolve_preview_action


def _load_linked_raw_event(db: Session, discrepancy: ReconciliationDiscrepancy) -> dict[str, Any] | None:
    meta = discrepancy.metadata_json if isinstance(discrepancy.metadata_json, dict) else {}
    chain_id = meta.get("chain_id")
    tx_hash = meta.get("tx_hash") or discrepancy.reference_id
    log_index = meta.get("log_index", 0)
    if chain_id is None or not tx_hash:
        return None
    row = RawOnChainEventRepository.find_by_chain_tx_log(
        db,
        chain_id=int(chain_id),
        tx_hash=str(tx_hash),
        log_index=int(log_index),
    )
    if row is None:
        return None
    return {
        "id": str(row.id),
        "chain_id": row.chain_id,
        "tx_hash": row.tx_hash,
        "log_index": row.log_index,
        "wallet_address": row.wallet_address,
        "asset": row.asset,
        "amount_raw": str(row.amount_raw),
        "block_number": int(row.block_number) if row.block_number is not None else None,
        "event_type": row.event_type,
        "payload_json": row.payload_json,
        "consumed_by_correction_id": (
            str(row.consumed_by_correction_id)
            if getattr(row, "consumed_by_correction_id", None)
            else None
        ),
    }


def list_discrepancies_admin(
    db: Session,
    *,
    filters: dict[str, Any],
    skip: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    rows, total = DiscrepancyRepository.list_filtered(db, skip=skip, limit=limit, **filters)
    items = [
        enrich_discrepancy_dict(db, discrepancy_to_dict(r), row=r, include_proof=False)
        for r in rows
    ]
    return items, total


def get_discrepancy_detail(db: Session, discrepancy_id: UUID) -> dict[str, Any] | None:
    row = DiscrepancyRepository.find_by_id(db, discrepancy_id)
    if row is None:
        return None
    corrections = (
        db.query(ReconciliationCorrection)
        .filter(ReconciliationCorrection.discrepancy_id == discrepancy_id)
        .order_by(ReconciliationCorrection.created_at.desc())
        .limit(50)
        .all()
    )
    raw_event = _load_linked_raw_event(db, row)
    disc = discrepancy_to_dict(row)
    enriched = enrich_discrepancy_dict(db, disc, row=row, raw_event=raw_event, include_proof=True)
    from .intent_admin_service import get_intent_for_discrepancy

    transaction_intent = get_intent_for_discrepancy(
        db,
        reference_type=row.reference_type,
        reference_id=row.reference_id,
        metadata_json=row.metadata_json if isinstance(row.metadata_json, dict) else None,
    )

    return {
        "discrepancy": disc,
        "likely_sources": enriched["likely_sources"],
        "auto_fix_risk": enriched["auto_fix_risk"],
        "onchain_proof": enriched["onchain_proof"],
        "raw_onchain_event": raw_event,
        "transaction_intent": transaction_intent,
        "corrections": [correction_to_dict(c) for c in corrections],
    }


def acknowledge_discrepancy(
    db: Session,
    *,
    discrepancy_id: UUID,
    actor_id: str,
    note: str | None,
) -> dict[str, Any]:
    row = _require_discrepancy(db, discrepancy_id)
    patch: dict[str, Any] = {
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "acknowledged_by": actor_id,
    }
    if note:
        patch["acknowledge_note"] = note
    updated = DiscrepancyRepository.update_status(
        db,
        row,
        status="acknowledged",
        resolved=False,
        metadata_patch=patch,
    )
    record_correction_request(
        db,
        discrepancy_id=discrepancy_id,
        action="acknowledge",
        requested_by=actor_id,
        before_json={"status": row.status},
        after_json={"status": "acknowledged"},
        dry_run=True,
        metadata_json={"phase": "5A", "allowed_to_apply": False},
    )
    return discrepancy_to_dict(updated)


def ignore_discrepancy(
    db: Session,
    *,
    discrepancy_id: UUID,
    actor_id: str,
    note: str | None,
) -> dict[str, Any]:
    row = _require_discrepancy(db, discrepancy_id)
    patch: dict[str, Any] = {
        "ignored_at": datetime.now(timezone.utc).isoformat(),
        "ignored_by": actor_id,
    }
    if note:
        patch["ignore_note"] = note
    updated = DiscrepancyRepository.update_status(
        db,
        row,
        status="ignored",
        resolved=True,
        metadata_patch=patch,
    )
    record_correction_request(
        db,
        discrepancy_id=discrepancy_id,
        action="ignore",
        requested_by=actor_id,
        before_json={"status": row.status},
        after_json={"status": "ignored"},
        dry_run=True,
        metadata_json={"phase": "5A", "allowed_to_apply": False},
    )
    return discrepancy_to_dict(updated)


def resolve_manually(
    db: Session,
    *,
    discrepancy_id: UUID,
    actor_id: str,
    note: str,
    resolution_code: str | None,
    extra_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    row = _require_discrepancy(db, discrepancy_id)
    patch: dict[str, Any] = {
        "resolved_manually_at": datetime.now(timezone.utc).isoformat(),
        "resolved_manually_by": actor_id,
        "resolution_note": note,
    }
    if resolution_code:
        patch["resolution_code"] = resolution_code
    if extra_metadata:
        patch.update(extra_metadata)
    updated = DiscrepancyRepository.update_status(
        db,
        row,
        status="resolved",
        resolved=True,
        metadata_patch=patch,
    )
    record_correction_request(
        db,
        discrepancy_id=discrepancy_id,
        action="resolve_manually",
        requested_by=actor_id,
        before_json={"status": row.status},
        after_json={"status": "resolved", "resolution_code": resolution_code},
        dry_run=True,
        metadata_json={"phase": "5A", "allowed_to_apply": False, "note": note},
    )
    return discrepancy_to_dict(updated)


def preview_correction(
    db: Session,
    *,
    discrepancy_id: UUID,
    actor_id: str,
    explicit_action: str | None,
) -> dict[str, Any]:
    row = _require_discrepancy(db, discrepancy_id)
    action = resolve_preview_action(row, explicit_action=explicit_action)
    assert_no_destructive_apply(action=action, allowed_to_apply=False)
    raw_event = _load_linked_raw_event(db, row)
    from .correction_policy import compute_allowed_to_apply, discrepancy_has_verified_raw_event

    has_raw, raw_row = discrepancy_has_verified_raw_event(db, row)
    raw_dict = raw_event
    if raw_row and not raw_dict:
        raw_dict = {
            "id": str(raw_row.id),
            "tx_hash": raw_row.tx_hash,
            "log_index": raw_row.log_index,
            "asset": raw_row.asset,
        }
    allowed = compute_allowed_to_apply(
        db,
        row,
        action=action,
        raw_event_id=UUID(str(raw_row.id)) if raw_row else None,
    )
    preview = build_correction_preview(
        row,
        action=action,
        raw_event=raw_dict,
        allowed_to_apply=allowed,
    )
    correction = record_correction_request(
        db,
        discrepancy_id=discrepancy_id,
        action=action,
        requested_by=actor_id,
        before_json=preview["before_json"],
        after_json=preview["after_json"],
        dry_run=True,
        metadata_json={
            "phase": "5B_preview",
            "allowed_to_apply": preview["allowed_to_apply"],
            "risk_level": preview["risk_level"],
            "requires_second_approval": preview["requires_second_approval"],
            "raw_onchain_event_id": raw_dict.get("id") if raw_dict else None,
        },
    )
    return {
        **preview,
        "correction_id": str(correction.id),
    }


def _require_discrepancy(db: Session, discrepancy_id: UUID) -> ReconciliationDiscrepancy:
    row = DiscrepancyRepository.find_by_id(db, discrepancy_id)
    if row is None:
        raise LookupError("discrepancy_not_found")
    return row
