"""B5 — Bundle parent controller minimal (agrégateur de preuves).

Tous les children du plan gelé doivent être ``LEDGER_SETTLED`` (B3c) avant
transition parent ``RECONCILED``. Pas de ``COMPLETED`` · pas de réparation ·
pas de replanification · pas de release lock v1.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_CHILD_REPORT_KEY,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
)
from services.portfolio_engine.bundles.event_driven.bundle_parent_controller_config import (
    bundle_parent_controller_enabled,
)
from services.transaction_intents.bundle_parent_child_repository import (
    find_children,
    is_bundle_parent_intent,
)

PHASE_CHILD_LEGS_CREATED = "CHILD_LEGS_CREATED"
PHASE_RECONCILED = "RECONCILED"
PHASE_COMPLETED = "COMPLETED"
HANDLER_VERSION = "bundle_parent_controller_v1"
PARENT_RECONCILIATION_BLOCK_KEY = "bundle_parent_reconciliation"
PARENT_REPORT_HASH_KEY = "parent_report_hash"


class BundleParentControllerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class BundleParentReconcileResult:
    skipped: bool
    idempotent: bool
    reconciled: bool
    parent_intent_id: UUID
    parent_report_hash: str | None
    plan_hash: str | None
    child_report_hashes: tuple[str, ...]
    reason: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parent_metadata(intent: TransactionIntent) -> dict[str, Any]:
    if isinstance(intent.metadata_json, dict):
        return intent.metadata_json
    return {}


def _child_settlement_block(child: TransactionIntent) -> dict[str, Any]:
    meta = _parent_metadata(child)
    block = meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY)
    if isinstance(block, dict):
        return block
    return {}


def _planned_leg_indices(parent_meta: dict[str, Any]) -> list[int]:
    plan_body = parent_meta.get("rebalance_plan_after_funding")
    if not isinstance(plan_body, dict):
        raise BundleParentControllerError(
            "bundle.parent_controller.missing_rebalance_plan",
            "rebalance_plan_after_funding requis",
        )
    legs = plan_body.get("legs")
    if not isinstance(legs, list) or not legs:
        raise BundleParentControllerError(
            "bundle.parent_controller.empty_plan",
            "plan sans leg",
        )
    indices: list[int] = []
    for leg in legs:
        if not isinstance(leg, dict):
            raise BundleParentControllerError(
                "bundle.parent_controller.invalid_plan_leg",
                "leg plan invalide",
            )
        raw_index = leg.get("leg_index")
        if raw_index is None:
            raise BundleParentControllerError(
                "bundle.parent_controller.missing_leg_index",
                "leg_index requis sur chaque leg du plan",
            )
        indices.append(int(raw_index))
    return sorted(indices)


def compute_parent_report_hash(
    *,
    parent_intent_id: UUID,
    plan_hash: str,
    planner_version: str,
    child_reports: list[tuple[int, str]],
) -> str:
    payload = {
        "parent_intent_id": str(parent_intent_id),
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "child_reports": [
            {"leg_index": leg_index, "child_report_hash": child_report_hash}
            for leg_index, child_report_hash in sorted(child_reports, key=lambda item: item[0])
        ],
        "handler": HANDLER_VERSION,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _validate_parent_shape(parent: TransactionIntent) -> dict[str, Any]:
    if not is_bundle_parent_intent(parent):
        raise BundleParentControllerError(
            "bundle.parent_controller.invalid_parent_shape",
            "parent bundle_invest intent_role=parent requis",
        )

    meta = _parent_metadata(parent)
    phase = str(meta.get("phase") or "").strip()
    if phase == PHASE_COMPLETED:
        raise BundleParentControllerError(
            "bundle.parent_controller.parent_completed",
            "parent COMPLETED — hors scope B5 v1",
        )

    plan_hash = str(meta.get("plan_hash") or "").strip()
    planner_version = str(meta.get("planner_version") or "").strip()
    if not plan_hash:
        raise BundleParentControllerError(
            "bundle.parent_controller.missing_plan_hash",
            "plan_hash requis",
        )
    if not planner_version:
        raise BundleParentControllerError(
            "bundle.parent_controller.missing_planner_version",
            "planner_version requis",
        )

    allowed_phases = {PHASE_CHILD_LEGS_CREATED, PHASE_RECONCILED}
    if phase and phase not in allowed_phases:
        raise BundleParentControllerError(
            "bundle.parent_controller.parent_phase_invalid",
            f"phase={phase!r} — CHILD_LEGS_CREATED ou RECONCILED attendu",
        )

    return {
        "phase": phase,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "planned_leg_indices": _planned_leg_indices(meta),
    }


def _collect_child_reports(
    *,
    children: list[TransactionIntent],
    planned_leg_indices: list[int],
    plan_hash: str,
) -> list[tuple[int, str]]:
    by_leg_index: dict[int, TransactionIntent] = {}
    for child in children:
        if child.leg_index is None:
            raise BundleParentControllerError(
                "bundle.parent_controller.child_missing_leg_index",
                f"child {child.id} sans leg_index",
            )
        leg_index = int(child.leg_index)
        if leg_index in by_leg_index:
            raise BundleParentControllerError(
                "bundle.parent_controller.duplicate_child_leg",
                f"leg_index={leg_index} dupliqué",
            )
        by_leg_index[leg_index] = child

    reports: list[tuple[int, str]] = []
    for leg_index in planned_leg_indices:
        child = by_leg_index.get(leg_index)
        if child is None:
            raise BundleParentControllerError(
                "bundle.parent_controller.child_missing",
                f"child manquant pour leg_index={leg_index}",
            )
        settlement = _child_settlement_block(child)
        child_phase = str(settlement.get("phase") or "").strip()
        if child_phase != BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED:
            raise BundleParentControllerError(
                "bundle.parent_controller.child_not_settled",
                f"leg_index={leg_index} phase={child_phase!r} — LEDGER_SETTLED requis",
            )
        child_plan_hash = str(settlement.get("plan_hash") or meta_plan_hash(child) or "").strip()
        if child_plan_hash != plan_hash:
            raise BundleParentControllerError(
                "bundle.parent_controller.plan_hash_mismatch",
                f"leg_index={leg_index} plan_hash child ≠ parent",
            )
        child_report_hash = str(
            settlement.get(BUNDLE_LEG_CHILD_REPORT_KEY) or ""
        ).strip()
        if not child_report_hash:
            raise BundleParentControllerError(
                "bundle.parent_controller.missing_child_report_hash",
                f"leg_index={leg_index} child_report_hash requis",
            )
        reports.append((leg_index, child_report_hash))

    extra_indices = set(by_leg_index) - set(planned_leg_indices)
    if extra_indices:
        raise BundleParentControllerError(
            "bundle.parent_controller.unexpected_children",
            f"children hors plan : {sorted(extra_indices)}",
        )

    return reports


def meta_plan_hash(child: TransactionIntent) -> str | None:
    meta = _parent_metadata(child)
    raw = meta.get("plan_hash")
    return str(raw).strip() if raw else None


def reconcile_bundle_parent_idempotently(
    db: Session,
    *,
    parent_intent_id: UUID,
) -> BundleParentReconcileResult:
    """Agrège les preuves child → parent RECONCILED — idempotent."""
    if not bundle_parent_controller_enabled():
        raise BundleParentControllerError(
            "bundle.parent_controller.disabled",
            "BUNDLE_PARENT_CONTROLLER_ENABLED requis",
        )

    parent = db.query(TransactionIntent).filter(TransactionIntent.id == parent_intent_id).first()
    if parent is None:
        raise BundleParentControllerError(
            "bundle.parent_controller.parent_not_found",
            f"parent_intent_id={parent_intent_id}",
        )

    ctx = _validate_parent_shape(parent)
    plan_hash = ctx["plan_hash"]
    planner_version = ctx["planner_version"]
    planned_leg_indices: list[int] = ctx["planned_leg_indices"]

    children = find_children(db, parent_intent_id=parent_intent_id)
    child_reports = _collect_child_reports(
        children=children,
        planned_leg_indices=planned_leg_indices,
        plan_hash=plan_hash,
    )
    parent_report_hash = compute_parent_report_hash(
        parent_intent_id=parent_intent_id,
        plan_hash=plan_hash,
        planner_version=planner_version,
        child_reports=child_reports,
    )
    child_report_hashes = tuple(hash_value for _, hash_value in sorted(child_reports))

    meta = dict(_parent_metadata(parent))
    existing_phase = str(meta.get("phase") or "").strip()
    existing_report = str(meta.get(PARENT_REPORT_HASH_KEY) or "").strip()
    if existing_phase == PHASE_RECONCILED and existing_report == parent_report_hash:
        return BundleParentReconcileResult(
            skipped=False,
            idempotent=True,
            reconciled=True,
            parent_intent_id=parent_intent_id,
            parent_report_hash=parent_report_hash,
            plan_hash=plan_hash,
            child_report_hashes=child_report_hashes,
            reason="parent_already_reconciled",
        )

    meta["phase"] = PHASE_RECONCILED
    meta[PARENT_REPORT_HASH_KEY] = parent_report_hash
    meta[PARENT_RECONCILIATION_BLOCK_KEY] = {
        "version": HANDLER_VERSION,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "child_report_hashes": [
            {"leg_index": leg_index, "child_report_hash": child_report_hash}
            for leg_index, child_report_hash in sorted(child_reports)
        ],
        "reconciled_at": _utc_now_iso(),
    }
    parent.metadata_json = meta
    db.add(parent)

    return BundleParentReconcileResult(
        skipped=False,
        idempotent=False,
        reconciled=True,
        parent_intent_id=parent_intent_id,
        parent_report_hash=parent_report_hash,
        plan_hash=plan_hash,
        child_report_hashes=child_report_hashes,
        reason=None,
    )
