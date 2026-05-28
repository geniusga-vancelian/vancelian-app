"""Stub corrections — enregistrement audit uniquement (Phase 4, pas d'apply balance)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .discrepancy_models import ReconciliationCorrection


class CorrectionNotAllowedError(RuntimeError):
    """Apply destructif interdit en Phase 4."""


FORBIDDEN_ACTIONS = frozenset(
    {
        "void_deposit",
        "adjust_balance",
        "rebuild_balance",
        "delete_deposit",
        "force_settlement",
        "apply",
        "apply_correction",
    }
)

PHASE_5A_ALLOWED_ACTIONS = frozenset(
    {
        "link_deposit_to_raw_event",
        "mark_admin_sim_as_phantom_candidate",
        "mark_swap_settlement_missing_actual_amount",
        "mark_onchain_event_missing_ledger_entry",
        "acknowledge",
        "ignore",
        "resolve_manually",
    }
)


def assert_no_destructive_apply(*, action: str, allowed_to_apply: bool = False) -> None:
    """Garde-fou Phase 5A — aucune apply balance / void / rebuild."""
    normalized = action.strip().lower()
    if normalized in FORBIDDEN_ACTIONS:
        raise CorrectionNotAllowedError(f"Action '{action}' interdite.")
    if allowed_to_apply:
        raise CorrectionNotAllowedError(
            "allowed_to_apply=true interdit en Phase 5A — preview uniquement.",
        )


def record_correction_request(
    db: Session,
    *,
    discrepancy_id: UUID,
    action: str,
    requested_by: str | None = None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
    dry_run: bool = True,
    metadata_json: dict[str, Any] | None = None,
) -> ReconciliationCorrection:
    """
    Enregistre une demande de correction (audit trail).

    Les actions destructives lèvent ``CorrectionNotAllowedError``.
    """
    normalized_action = action.strip().lower()
    assert_no_destructive_apply(action=normalized_action, allowed_to_apply=False)
    if normalized_action in FORBIDDEN_ACTIONS:
        raise CorrectionNotAllowedError(
            f"Action '{action}' interdite — aucune modification de balance autorisée.",
        )

    meta = dict(metadata_json or {})
    meta.setdefault("allowed_to_apply", False)
    meta.setdefault("phase", "5A")

    row = ReconciliationCorrection(
        discrepancy_id=discrepancy_id,
        action=normalized_action,
        status="preview",
        before_json=before_json,
        after_json=after_json,
        requested_by=requested_by,
        approved_by=None,
        dry_run=dry_run,
        applied_at=None if dry_run else datetime.now(timezone.utc),
        metadata_json=meta,
    )
    db.add(row)
    db.flush()
    return row


def correction_to_dict(row: ReconciliationCorrection) -> dict:
    from .discrepancy_repository import _iso_dt

    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return {
        "id": str(row.id),
        "discrepancy_id": str(row.discrepancy_id),
        "action": row.action,
        "status": getattr(row, "status", "preview"),
        "before_json": row.before_json,
        "after_json": row.after_json,
        "requested_by": row.requested_by,
        "approved_by": row.approved_by,
        "applied_by": meta.get("applied_by"),
        "rejected_by": meta.get("rejected_by"),
        "reject_reason": meta.get("reject_reason"),
        "requested_at": _iso_dt(row.created_at),
        "approved_at": meta.get("approved_at"),
        "dry_run": bool(row.dry_run),
        "applied_at": _iso_dt(row.applied_at),
        "metadata_json": row.metadata_json,
        "created_at": _iso_dt(row.created_at),
    }
