"""B4a — Bundle child factory (parent FROZEN → child #0 auto · no swap · no settlement).

Crée 1 child intent depuis un parent ``bundle_invest`` en phase ``REBALANCE_PLAN_FROZEN``.
Aucun wiring runtime worker/outbox/LI.FI/settlement.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.bundle_parent_child_repository import (
    bundle_child_idempotency_key,
    find_bundle_leg,
    is_bundle_parent_intent,
)
from services.transaction_intents.enums import (
    IntentOperationType,
    IntentProductType,
    IntentRole,
    IntentStatus,
)

PHASE_REBALANCE_PLAN_FROZEN = "REBALANCE_PLAN_FROZEN"
PHASE_CHILD_LEGS_CREATED = "CHILD_LEGS_CREATED"
CHILD_STATUS_AWAITING_SWAP = "awaiting_swap"
HANDLER_VERSION = "bundle_child_factory_v1"

B4A_LEG_INDEX = 0
B4A_DIRECTION_BUY = "buy"
B4A_FROM_ASSET = "USDC"
B4A_TO_ASSET = "AAVE"
B4A_CHAIN = "base"


class BundleChildFactoryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class BundleChildFactoryResult:
    created: bool
    idempotent: bool
    parent_intent_id: UUID
    child_intent_id: UUID | None
    leg_index: int
    plan_hash: str | None
    planner_version: str | None
    child_intent_ids: tuple[str, ...]
    reason: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parent_metadata(intent: TransactionIntent) -> dict[str, Any]:
    if isinstance(intent.metadata_json, dict):
        return intent.metadata_json
    return {}


def _normalize_chain(value: str | None) -> str:
    return str(value or B4A_CHAIN).strip().lower()


def _normalize_asset(value: str | None) -> str:
    return str(value or "").strip().upper()


def _parse_notional_usdc(leg: dict[str, Any]) -> str:
    for key in ("notional_usdc", "amount_in_usdc", "planned_amount_in"):
        raw = leg.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    raise BundleChildFactoryError(
        "bundle.child_factory.missing_notional_usdc",
        "notional_usdc requis sur la leg #0",
    )


def _parse_frozen_leg(plan_body: dict[str, Any]) -> dict[str, Any]:
    legs = plan_body.get("legs")
    if not isinstance(legs, list):
        raise BundleChildFactoryError(
            "bundle.child_factory.invalid_plan_legs",
            "rebalance_plan_after_funding.legs invalide",
        )
    if len(legs) == 0:
        raise BundleChildFactoryError(
            "bundle.child_factory.empty_plan",
            "plan sans leg — B4a v1 exige exactement 1 leg",
        )
    if len(legs) != 1:
        raise BundleChildFactoryError(
            "bundle.child_factory.multiple_legs_not_allowed_b4a",
            f"B4a v1 : {len(legs)} legs — exactement 1 attendu",
        )

    leg = legs[0]
    if not isinstance(leg, dict):
        raise BundleChildFactoryError(
            "bundle.child_factory.invalid_leg_shape",
            "leg #0 invalide",
        )

    leg_index = leg.get("leg_index")
    if leg_index is None:
        leg_index = B4A_LEG_INDEX
    if int(leg_index) != B4A_LEG_INDEX:
        raise BundleChildFactoryError(
            "bundle.child_factory.invalid_leg_index",
            f"leg_index={leg_index} — B4a v1 exige leg_index=0",
        )

    direction = str(leg.get("direction") or "").strip().lower()
    if direction != B4A_DIRECTION_BUY:
        raise BundleChildFactoryError(
            "bundle.child_factory.sell_not_allowed_b4a",
            f"direction={direction} — B4a v1 BUY only",
        )

    from_asset = _normalize_asset(leg.get("from_asset"))
    to_asset = _normalize_asset(leg.get("to_asset") or leg.get("asset"))
    if not from_asset:
        from_asset = B4A_FROM_ASSET
    if from_asset != B4A_FROM_ASSET or to_asset != B4A_TO_ASSET:
        raise BundleChildFactoryError(
            "bundle.child_factory.invalid_asset_pair_b4a",
            f"Paire {from_asset}→{to_asset} hors scope B4a v1 (USDC→AAVE)",
        )

    from_chain = _normalize_chain(leg.get("from_chain"))
    to_chain = _normalize_chain(leg.get("to_chain"))
    if from_chain != B4A_CHAIN or to_chain != B4A_CHAIN:
        raise BundleChildFactoryError(
            "bundle.child_factory.chain_not_base_b4a",
            f"chains {from_chain}/{to_chain} — Base/Base requis",
        )

    return {
        "leg_index": B4A_LEG_INDEX,
        "leg_direction": direction,
        "from_asset": from_asset,
        "to_asset": to_asset,
        "from_chain": from_chain,
        "to_chain": to_chain,
        "notional_usdc": _parse_notional_usdc(leg),
    }


def _validate_parent_frozen(parent: TransactionIntent) -> dict[str, Any]:
    if not is_bundle_parent_intent(parent):
        raise BundleChildFactoryError(
            "bundle.child_factory.invalid_parent_shape",
            "parent bundle_invest intent_role=parent requis",
        )

    meta = _parent_metadata(parent)
    phase = str(meta.get("phase") or "").strip()
    if phase != PHASE_REBALANCE_PLAN_FROZEN:
        raise BundleChildFactoryError(
            "bundle.child_factory.parent_not_frozen",
            f"phase={phase!r} — REBALANCE_PLAN_FROZEN requis",
        )

    plan_hash = str(meta.get("plan_hash") or "").strip()
    planner_version = str(meta.get("planner_version") or "").strip()
    if not plan_hash:
        raise BundleChildFactoryError(
            "bundle.child_factory.missing_plan_hash",
            "plan_hash requis sur parent metadata",
        )
    if not planner_version:
        raise BundleChildFactoryError(
            "bundle.child_factory.missing_planner_version",
            "planner_version requis sur parent metadata",
        )

    plan_body = meta.get("rebalance_plan_after_funding")
    if not isinstance(plan_body, dict):
        raise BundleChildFactoryError(
            "bundle.child_factory.missing_rebalance_plan",
            "rebalance_plan_after_funding requis",
        )

    leg = _parse_frozen_leg(plan_body)
    portfolio_id = str(meta.get("portfolio_id") or meta.get("bundle_id") or "").strip() or None

    return {
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "portfolio_id": portfolio_id,
        **leg,
    }


def _sync_parent_child_metadata(
    parent: TransactionIntent,
    *,
    child_id: UUID,
    plan_hash: str,
    planner_version: str,
) -> None:
    meta = dict(_parent_metadata(parent))
    existing_ids = meta.get("child_intent_ids")
    child_ids: list[str]
    if isinstance(existing_ids, list):
        child_ids = [str(x) for x in existing_ids if str(x).strip()]
    else:
        child_ids = []
    child_str = str(child_id)
    if child_str not in child_ids:
        child_ids.append(child_str)
    meta["phase"] = PHASE_CHILD_LEGS_CREATED
    meta["child_intent_ids"] = child_ids
    meta["child_factory"] = {
        "version": HANDLER_VERSION,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "updated_at": _utc_now_iso(),
    }
    parent.metadata_json = meta


def create_bundle_child_intents_from_frozen_plan(
    db: Session,
    *,
    parent_intent_id: UUID,
) -> BundleChildFactoryResult:
    """Crée child #0 depuis parent FROZEN — idempotent par (parent, leg_index)."""
    parent = db.query(TransactionIntent).filter(TransactionIntent.id == parent_intent_id).first()
    if parent is None:
        raise BundleChildFactoryError(
            "bundle.child_factory.parent_not_found",
            f"parent_intent_id={parent_intent_id}",
        )

    ctx = _validate_parent_frozen(parent)
    existing = find_bundle_leg(db, parent_intent_id=parent_intent_id, leg_index=B4A_LEG_INDEX)
    if existing is not None:
        _sync_parent_child_metadata(
            parent,
            child_id=existing.id,
            plan_hash=ctx["plan_hash"],
            planner_version=ctx["planner_version"],
        )
        db.add(parent)
        db.flush()
        meta = _parent_metadata(parent)
        child_ids = tuple(str(x) for x in (meta.get("child_intent_ids") or []))
        return BundleChildFactoryResult(
            created=False,
            idempotent=True,
            parent_intent_id=parent_intent_id,
            child_intent_id=existing.id,
            leg_index=B4A_LEG_INDEX,
            plan_hash=ctx["plan_hash"],
            planner_version=ctx["planner_version"],
            child_intent_ids=child_ids,
            reason="child_leg_already_exists",
        )

    child_meta: dict[str, Any] = {
        "planner_version": ctx["planner_version"],
        "plan_hash": ctx["plan_hash"],
        "leg_index": ctx["leg_index"],
        "leg_direction": ctx["leg_direction"],
        "from_asset": ctx["from_asset"],
        "to_asset": ctx["to_asset"],
        "from_chain": ctx["from_chain"],
        "to_chain": ctx["to_chain"],
        "notional_usdc": ctx["notional_usdc"],
        "status": CHILD_STATUS_AWAITING_SWAP,
        "bundle_child_factory": {
            "version": HANDLER_VERSION,
            "created_at": _utc_now_iso(),
        },
    }
    if ctx.get("portfolio_id"):
        child_meta["portfolio_id"] = ctx["portfolio_id"]

    child = TransactionIntent(
        person_id=parent.person_id,
        product_type=IntentProductType.BUNDLE_LEG.value,
        operation_type=IntentOperationType.BUNDLE_LEG.value,
        idempotency_key=bundle_child_idempotency_key(
            parent_intent_id=parent_intent_id,
            leg_index=B4A_LEG_INDEX,
        ),
        status=IntentStatus.CREATED.value,
        intent_role=IntentRole.CHILD.value,
        parent_intent_id=parent_intent_id,
        leg_index=B4A_LEG_INDEX,
        bundle_execution_id=parent.bundle_execution_id,
        metadata_json=child_meta,
    )
    db.add(child)
    db.flush()

    _sync_parent_child_metadata(
        parent,
        child_id=child.id,
        plan_hash=ctx["plan_hash"],
        planner_version=ctx["planner_version"],
    )
    db.add(parent)
    db.flush()

    parent_meta = _parent_metadata(parent)
    child_ids = tuple(str(x) for x in (parent_meta.get("child_intent_ids") or []))

    return BundleChildFactoryResult(
        created=True,
        idempotent=False,
        parent_intent_id=parent_intent_id,
        child_intent_id=child.id,
        leg_index=B4A_LEG_INDEX,
        plan_hash=ctx["plan_hash"],
        planner_version=ctx["planner_version"],
        child_intent_ids=child_ids,
    )
