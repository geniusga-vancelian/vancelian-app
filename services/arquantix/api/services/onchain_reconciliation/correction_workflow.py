"""Workflow request / approve / reject / apply (Phase 5B)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .correction_apply import CorrectionApplyError, apply_correction
from .correction_policy import (
    APPLY_WHITELIST_ACTIONS,
    CORRECTION_STATUS_APPROVED,
    CORRECTION_STATUS_REJECTED,
    CORRECTION_STATUS_REQUESTED,
    CorrectionPolicyError,
    compute_allowed_to_apply,
    discrepancy_has_verified_raw_event,
    load_raw_event,
    validate_approver_separation,
    validate_discrepancy_applyable,
    validate_raw_event_for_discrepancy,
)
from .raw_event_consumption import RawEventConsumptionError
from .correction_service import correction_to_dict
from .discrepancy_models import ReconciliationCorrection, ReconciliationDiscrepancy
from .discrepancy_repository import DiscrepancyRepository, discrepancy_to_dict
from .preview_service import build_correction_preview


class CorrectionWorkflowError(ValueError):
    pass


def _get_correction(db: Session, correction_id: UUID) -> ReconciliationCorrection:
    row = db.query(ReconciliationCorrection).filter(ReconciliationCorrection.id == correction_id).first()
    if row is None:
        raise LookupError("correction_not_found")
    return row


def _get_discrepancy(db: Session, discrepancy_id: UUID) -> ReconciliationDiscrepancy:
    row = DiscrepancyRepository.find_by_id(db, discrepancy_id)
    if row is None:
        raise LookupError("discrepancy_not_found")
    return row


def request_correction(
    db: Session,
    *,
    discrepancy_id: UUID,
    action: str,
    requested_by: str,
    raw_onchain_event_id: UUID | None = None,
    deposit_id: UUID | None = None,
) -> dict[str, Any]:
    discrepancy = _get_discrepancy(db, discrepancy_id)
    normalized = action.strip().lower()
    if normalized not in APPLY_WHITELIST_ACTIONS:
        raise CorrectionWorkflowError(f"action_not_whitelisted:{action}")

    try:
        validate_discrepancy_applyable(discrepancy)
    except CorrectionPolicyError as exc:
        raise CorrectionWorkflowError(str(exc)) from exc

    has_raw, raw_row = discrepancy_has_verified_raw_event(
        db,
        discrepancy,
        raw_event_id=raw_onchain_event_id,
    )
    if normalized in APPLY_WHITELIST_ACTIONS and not has_raw:
        raise CorrectionWorkflowError("apply_disabled_missing_raw_onchain_event_proof")

    if raw_onchain_event_id and raw_row is None:
        raw_row = load_raw_event(db, raw_onchain_event_id)
    if raw_row is not None:
        try:
            validate_raw_event_for_discrepancy(db, discrepancy, raw_row)
        except RawEventConsumptionError as exc:
            raise CorrectionWorkflowError(str(exc)) from exc

    allowed = compute_allowed_to_apply(
        db,
        discrepancy,
        action=normalized,
        raw_event_id=raw_onchain_event_id or (UUID(str(raw_row.id)) if raw_row else None),
        deposit_id=deposit_id,
    )
    if not allowed:
        raise CorrectionWorkflowError("correction_not_allowed_to_apply")

    raw_dict = None
    if raw_row is not None:
        raw_dict = {
            "id": str(raw_row.id),
            "chain_id": raw_row.chain_id,
            "tx_hash": raw_row.tx_hash,
            "log_index": raw_row.log_index,
            "wallet_address": raw_row.wallet_address,
            "asset": raw_row.asset,
            "amount_raw": str(raw_row.amount_raw),
        }

    preview = build_correction_preview(
        discrepancy,
        action=normalized,
        raw_event=raw_dict,
        allowed_to_apply=allowed,
    )

    row = ReconciliationCorrection(
        discrepancy_id=discrepancy_id,
        action=normalized,
        status=CORRECTION_STATUS_REQUESTED,
        before_json=preview["before_json"],
        after_json=preview["after_json"],
        requested_by=requested_by,
        approved_by=None,
        dry_run=True,
        applied_at=None,
        metadata_json={
            "phase": "5C",
            "allowed_to_apply": allowed,
            "raw_onchain_event_id": str(raw_row.id) if raw_row else None,
            "deposit_id": str(deposit_id) if deposit_id else None,
            "requires_second_approval": preview["requires_second_approval"],
        },
    )
    db.add(row)
    db.flush()
    return correction_to_dict(row)


def approve_correction(
    db: Session,
    *,
    correction_id: UUID,
    approved_by: str,
) -> dict[str, Any]:
    correction = _get_correction(db, correction_id)
    if correction.status != CORRECTION_STATUS_REQUESTED:
        raise CorrectionWorkflowError("correction_not_in_requested_state")

    discrepancy = _get_discrepancy(db, correction.discrepancy_id)
    try:
        validate_discrepancy_applyable(discrepancy)
    except CorrectionPolicyError as exc:
        raise CorrectionWorkflowError(str(exc)) from exc

    validate_approver_separation(
        requested_by=correction.requested_by,
        approved_by=approved_by,
    )

    correction.status = CORRECTION_STATUS_APPROVED
    correction.approved_by = approved_by
    meta = correction.metadata_json if isinstance(correction.metadata_json, dict) else {}
    from datetime import datetime, timezone

    correction.metadata_json = {
        **meta,
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    db.add(correction)
    db.flush()
    return correction_to_dict(correction)


def reject_correction(
    db: Session,
    *,
    correction_id: UUID,
    rejected_by: str,
    reason: str | None = None,
) -> dict[str, Any]:
    correction = _get_correction(db, correction_id)
    if correction.status not in (CORRECTION_STATUS_REQUESTED, CORRECTION_STATUS_APPROVED):
        raise CorrectionWorkflowError("correction_not_rejectable")

    correction.status = CORRECTION_STATUS_REJECTED
    meta = correction.metadata_json if isinstance(correction.metadata_json, dict) else {}
    correction.metadata_json = {**meta, "rejected_by": rejected_by, "reject_reason": reason}
    db.add(correction)
    db.flush()
    return correction_to_dict(correction)


def apply_approved_correction(
    db: Session,
    *,
    correction_id: UUID,
    actor_id: str,
) -> dict[str, Any]:
    correction = _get_correction(db, correction_id)
    discrepancy = _get_discrepancy(db, correction.discrepancy_id)

    try:
        validate_discrepancy_applyable(discrepancy)
    except CorrectionPolicyError as exc:
        raise CorrectionApplyError(str(exc)) from exc

    meta = correction.metadata_json if isinstance(correction.metadata_json, dict) else {}
    if not meta.get("allowed_to_apply"):
        raise CorrectionApplyError("allowed_to_apply_false")

    try:
        return apply_correction(
            db,
            correction=correction,
            discrepancy=discrepancy,
            actor_id=actor_id,
        )
    except CorrectionPolicyError as exc:
        raise CorrectionApplyError(str(exc)) from exc
