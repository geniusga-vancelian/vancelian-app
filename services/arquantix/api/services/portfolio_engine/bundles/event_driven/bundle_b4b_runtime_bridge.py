"""B4b — Bundle minimal runtime bridge (parent FROZEN → child → lock → swap → settle B3c).

Pont runtime minimal : 1 parent · 1 child · 1 buy leg USDC→AAVE Base/Base · fresh swap LI.FI.
Pas de Controller parent · pas de finalize · pas de COMPLETED · pas de WebApp.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_lifi_quote_service import BundleLifiQuoteService
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import is_bundle_internal_swap
from services.portfolio_engine.bundle_execution.lifi_base_config import BUNDLE_LIFI_CHAIN_KEY
from services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge_config import (
    bundle_b4b_runtime_bridge_enabled,
)
from services.portfolio_engine.bundles.event_driven.bundle_child_factory import (
    B4A_CHAIN,
    B4A_DIRECTION_BUY,
    B4A_FROM_ASSET,
    B4A_LEG_INDEX,
    B4A_TO_ASSET,
    CHILD_STATUS_AWAITING_SWAP,
    PHASE_CHILD_LEGS_CREATED,
    PHASE_REBALANCE_PLAN_FROZEN,
    create_bundle_child_intents_from_frozen_plan,
)
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED,
    BUNDLE_LEG_SETTLEMENT_BLOCK_KEY,
    settle_bundle_leg_idempotently,
)
from services.portfolio_engine.instruments.models import Instrument
from services.product_locks.exceptions import ProductLockConflict, TransactionInProgress409
from services.product_locks.global_user_transaction_lock import (
    acquire_global_user_transaction_lock,
    release_global_user_transaction_lock,
    transaction_in_progress_409_from_conflict,
)
from services.transaction_intents.bundle_parent_child_repository import (
    find_bundle_leg,
    find_children,
    is_bundle_parent_intent,
)

HANDLER_VERSION = "bundle_b4b_runtime_bridge_v1"
B4B_REASON = "bundle_b4b_minimal_bridge"
LINKED_SWAP_TABLE = "person_wallet_swaps"


class BundleB4bBridgeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class BundleB4bBridgeResult:
    skipped: bool
    idempotent: bool
    completed: bool
    parent_intent_id: UUID
    child_intent_id: UUID | None
    swap_id: UUID | None
    settled: bool
    global_lock_acquired: bool
    global_lock_released: bool
    awaiting_swap_confirmation: bool
    reason: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parent_metadata(intent: TransactionIntent) -> dict[str, Any]:
    if isinstance(intent.metadata_json, dict):
        return intent.metadata_json
    return {}


def _child_metadata(intent: TransactionIntent) -> dict[str, Any]:
    if isinstance(intent.metadata_json, dict):
        return intent.metadata_json
    return {}


def _child_awaiting_swap_status(child: TransactionIntent) -> str:
    meta = _child_metadata(child)
    return str(meta.get("status") or "").strip().lower()


def _child_already_ledger_settled(child: TransactionIntent) -> bool:
    meta = _child_metadata(child)
    block = meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY)
    if not isinstance(block, dict) or block.get("settled") is not True:
        return False
    phase = str(block.get("phase") or "").strip()
    return phase == BUNDLE_LEG_CHILD_PHASE_LEDGER_SETTLED


def _parse_notional_usdc(child_meta: dict[str, Any], parent_meta: dict[str, Any]) -> str:
    for source in (child_meta, parent_meta):
        for key in ("planned_amount_in", "notional_usdc", "amount_in_usdc"):
            raw = source.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip()
        plan = source.get("rebalance_plan_after_funding")
        if isinstance(plan, dict):
            legs = plan.get("legs")
            if isinstance(legs, list) and legs:
                leg0 = legs[0]
                if isinstance(leg0, dict):
                    for key in ("notional_usdc", "amount_in_usdc", "planned_amount_in"):
                        raw = leg0.get(key)
                        if raw is not None and str(raw).strip():
                            return str(raw).strip()
    raise BundleB4bBridgeError(
        "bundle.b4b.missing_notional_usdc",
        "notional_usdc requis pour fresh swap",
    )


def _validate_parent_b4b(parent: TransactionIntent) -> dict[str, Any]:
    if not is_bundle_parent_intent(parent):
        raise BundleB4bBridgeError(
            "bundle.b4b.invalid_parent_shape",
            "parent bundle_invest intent_role=parent requis",
        )

    meta = _parent_metadata(parent)
    phase = str(meta.get("phase") or "").strip()
    if phase not in {PHASE_REBALANCE_PLAN_FROZEN, PHASE_CHILD_LEGS_CREATED}:
        raise BundleB4bBridgeError(
            "bundle.b4b.parent_phase_not_allowed",
            f"phase={phase!r} — REBALANCE_PLAN_FROZEN ou CHILD_LEGS_CREATED requis",
        )

    plan_hash = str(meta.get("plan_hash") or "").strip()
    planner_version = str(meta.get("planner_version") or "").strip()
    if not plan_hash:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_plan_hash",
            "plan_hash requis sur parent metadata",
        )
    if not planner_version:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_planner_version",
            "planner_version requis sur parent metadata",
        )

    portfolio_id_raw = str(meta.get("portfolio_id") or meta.get("bundle_id") or "").strip()
    if not portfolio_id_raw:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_portfolio_id",
            "portfolio_id requis sur parent metadata",
        )

    return {
        "phase": phase,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "portfolio_id": UUID(portfolio_id_raw),
    }


def _resolve_usdc_aave_instrument_ids(db: Session) -> tuple[UUID, UUID]:
    usdc_asset = db.query(Asset).filter(Asset.symbol == B4A_FROM_ASSET).first()
    if usdc_asset is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_usdc_asset",
            "asset USDC introuvable",
        )
    usdc_instr = (
        db.query(Instrument)
        .filter(
            Instrument.asset_id == usdc_asset.id,
            Instrument.instrument_type == "spot",
        )
        .first()
    )
    if usdc_instr is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_usdc_instrument",
            "instrument USDC spot introuvable",
        )

    aave_asset = db.query(Asset).filter(Asset.symbol == B4A_TO_ASSET).first()
    if aave_asset is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_aave_asset",
            "asset AAVE introuvable",
        )
    aave_instr = (
        db.query(Instrument)
        .filter(
            Instrument.asset_id == aave_asset.id,
            Instrument.instrument_type == "spot",
        )
        .first()
    )
    if aave_instr is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_aave_instrument",
            "instrument AAVE spot introuvable",
        )
    return usdc_instr.id, aave_instr.id


def _enrich_child_pe_metadata(
    child: TransactionIntent,
    *,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
    target_instrument_id: UUID,
    planned_amount_in: str,
    swap: PersonWalletSwap | None = None,
) -> None:
    meta = dict(_child_metadata(child))
    meta["portfolio_id"] = str(portfolio_id)
    meta["entry_instrument_id"] = str(entry_instrument_id)
    meta["target_instrument_id"] = str(target_instrument_id)
    meta["planned_amount_in"] = planned_amount_in
    meta["leg_direction"] = B4A_DIRECTION_BUY
    meta["from_asset"] = B4A_FROM_ASSET
    meta["to_asset"] = B4A_TO_ASSET
    meta["from_chain"] = B4A_CHAIN
    meta["to_chain"] = B4A_CHAIN
    if swap is not None:
        tx_hash = str(swap.tx_hash or "").strip()
        if tx_hash:
            meta["tx_hash"] = tx_hash
    bridge = meta.get("bundle_b4b_bridge")
    if not isinstance(bridge, dict):
        bridge = {}
    bridge["version"] = HANDLER_VERSION
    bridge["updated_at"] = _utc_now_iso()
    meta["bundle_b4b_bridge"] = bridge
    child.metadata_json = meta


def _validate_single_child_awaiting_swap(children: list[TransactionIntent]) -> TransactionIntent:
    if len(children) == 0:
        raise BundleB4bBridgeError(
            "bundle.b4b.no_child_intent",
            "aucun child intent sous le parent",
        )
    if len(children) != 1:
        raise BundleB4bBridgeError(
            "bundle.b4b.multiple_children_not_allowed",
            f"{len(children)} children — B4b v1 exige exactement 1",
        )
    child = children[0]
    if child.leg_index is not None and int(child.leg_index) != B4A_LEG_INDEX:
        raise BundleB4bBridgeError(
            "bundle.b4b.invalid_leg_index",
            f"leg_index={child.leg_index} — B4b v1 exige leg_index=0",
        )
    if _child_already_ledger_settled(child):
        return child
    status = _child_awaiting_swap_status(child)
    if status and status not in {CHILD_STATUS_AWAITING_SWAP, CHILD_STATUS_SWAP_ATTACHED}:
        raise BundleB4bBridgeError(
            "bundle.b4b.child_not_awaiting_swap",
            f"child status={status!r} — awaiting_swap ou swap_attached requis",
        )
    return child


def _ensure_child_intent(
    db: Session,
    *,
    parent: TransactionIntent,
    parent_intent_id: UUID,
    parent_ctx: dict[str, Any],
) -> TransactionIntent:
    if parent_ctx["phase"] == PHASE_REBALANCE_PLAN_FROZEN:
        factory = create_bundle_child_intents_from_frozen_plan(
            db,
            parent_intent_id=parent_intent_id,
        )
        if factory.child_intent_id is None:
            raise BundleB4bBridgeError(
                "bundle.b4b.child_factory_failed",
                "B4a n'a pas produit de child_intent_id",
            )
        child = db.get(TransactionIntent, factory.child_intent_id)
        if child is None:
            raise BundleB4bBridgeError(
                "bundle.b4b.child_not_found_after_factory",
                f"child_intent_id={factory.child_intent_id}",
            )
        return child

    child = find_bundle_leg(db, parent_intent_id=parent_intent_id, leg_index=B4A_LEG_INDEX)
    if child is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_child_for_child_legs_created",
            "parent CHILD_LEGS_CREATED sans child leg #0",
        )
    return child


def _tag_swap_bundle_execution(
    swap: PersonWalletSwap,
    *,
    portfolio_id: UUID,
    parent_intent_id: UUID,
    child_intent_id: UUID,
    bundle_execution_id: UUID | None,
    plan_hash: str,
    planner_version: str,
    leg_index: int = B4A_LEG_INDEX,
) -> None:
    batch_id = str(bundle_execution_id or parent_intent_id)
    PersonWalletSwapRepository().append_audit(
        swap,
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "batch_id": batch_id,
            "leg_id": f"leg-{leg_index}",
            "leg_index": leg_index,
            "portfolio_id": str(portfolio_id),
            "bundle_action": "invest",
            "leg_action": "rebalance_buy",
            "execution_provider": "lifi_base",
            "parent_intent_id": str(parent_intent_id),
            "child_intent_id": str(child_intent_id),
            "plan_hash": plan_hash,
            "planner_version": planner_version,
        },
    )


def _create_fresh_bundle_swap(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    parent_intent_id: UUID,
    child_intent_id: UUID,
    notional_usdc: str,
    bundle_execution_id: UUID | None,
    plan_hash: str,
    planner_version: str,
) -> PersonWalletSwap:
    quote_svc = BundleLifiQuoteService()
    response = quote_svc.create_bundle_quote(
        db,
        person_id=person_id,
        from_asset=B4A_FROM_ASSET,
        to_asset=B4A_TO_ASSET,
        amount=notional_usdc,
        leg_action="rebalance_buy",
    )
    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == response.swap_id).first()
    if swap is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.swap_not_found_after_quote",
            f"swap_id={response.swap_id}",
        )
    _tag_swap_bundle_execution(
        swap,
        portfolio_id=portfolio_id,
        parent_intent_id=parent_intent_id,
        child_intent_id=child_intent_id,
        bundle_execution_id=bundle_execution_id,
        plan_hash=plan_hash,
        planner_version=planner_version,
    )
    db.add(swap)
    db.flush()
    return swap


CHILD_STATUS_SWAP_ATTACHED = "swap_attached"


def _attach_swap_to_child(
    db: Session,
    *,
    child: TransactionIntent,
    swap: PersonWalletSwap,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
    target_instrument_id: UUID,
    planned_amount_in: str,
) -> None:
    child.linked_table = LINKED_SWAP_TABLE
    child.linked_id = swap.id
    _enrich_child_pe_metadata(
        child,
        portfolio_id=portfolio_id,
        entry_instrument_id=entry_instrument_id,
        target_instrument_id=target_instrument_id,
        planned_amount_in=planned_amount_in,
        swap=swap,
    )
    meta = dict(_child_metadata(child))
    meta["status"] = CHILD_STATUS_SWAP_ATTACHED
    child.metadata_json = meta
    db.add(child)
    db.flush()


def _acquire_global_lock_or_409(
    db: Session,
    *,
    person_id: UUID,
    intent_id: UUID,
) -> bool:
    try:
        result = acquire_global_user_transaction_lock(
            db,
            person_id=person_id,
            intent_id=intent_id,
            reason=B4B_REASON,
        )
    except ProductLockConflict as exc:
        raise transaction_in_progress_409_from_conflict(
            exc,
            existing_reason=B4B_REASON,
            requested_reason=B4B_REASON,
        ) from exc
    return result.acquired or result.idempotent


def _release_global_lock(db: Session, *, intent_id: UUID) -> bool:
    result = release_global_user_transaction_lock(
        db,
        intent_id=intent_id,
        reason=B4B_REASON,
    )
    return result.released or result.idempotent


def _swap_is_confirmed(swap: PersonWalletSwap) -> bool:
    return (swap.status or "").upper() == SwapSessionStatus.CONFIRMED.value


def run_bundle_b4b_minimal_bridge(
    db: Session,
    *,
    parent_intent_id: UUID,
) -> BundleB4bBridgeResult:
    """Pont B4b minimal — flag OFF → no-op strict (aucune écriture · aucun swap · aucun settlement)."""
    if not bundle_b4b_runtime_bridge_enabled():
        return BundleB4bBridgeResult(
            skipped=True,
            idempotent=False,
            completed=False,
            parent_intent_id=parent_intent_id,
            child_intent_id=None,
            swap_id=None,
            settled=False,
            global_lock_acquired=False,
            global_lock_released=False,
            awaiting_swap_confirmation=False,
            reason="bundle_b4b_runtime_bridge_disabled",
        )

    parent = db.query(TransactionIntent).filter(TransactionIntent.id == parent_intent_id).first()
    if parent is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.parent_not_found",
            f"parent_intent_id={parent_intent_id}",
        )

    parent_ctx = _validate_parent_b4b(parent)
    person_id = parent.person_id
    if person_id is None:
        raise BundleB4bBridgeError(
            "bundle.b4b.missing_person_id",
            "person_id requis sur parent",
        )

    existing_child = find_bundle_leg(db, parent_intent_id=parent_intent_id, leg_index=B4A_LEG_INDEX)
    if existing_child is not None and _child_already_ledger_settled(existing_child):
        _release_global_lock(db, intent_id=parent_intent_id)
        return BundleB4bBridgeResult(
            skipped=False,
            idempotent=True,
            completed=True,
            parent_intent_id=parent_intent_id,
            child_intent_id=existing_child.id,
            swap_id=existing_child.linked_id,
            settled=True,
            global_lock_acquired=False,
            global_lock_released=True,
            awaiting_swap_confirmation=False,
            reason="child_already_ledger_settled",
        )

    lock_acquired = False
    try:
        lock_acquired = _acquire_global_lock_or_409(
            db,
            person_id=person_id,
            intent_id=parent_intent_id,
        )

        child = _ensure_child_intent(
            db,
            parent=parent,
            parent_intent_id=parent_intent_id,
            parent_ctx=parent_ctx,
        )
        children = find_children(db, parent_intent_id=parent_intent_id)
        child = _validate_single_child_awaiting_swap(children)

        if _child_already_ledger_settled(child):
            released = _release_global_lock(db, intent_id=parent_intent_id)
            return BundleB4bBridgeResult(
                skipped=False,
                idempotent=True,
                completed=True,
                parent_intent_id=parent_intent_id,
                child_intent_id=child.id,
                swap_id=child.linked_id,
                settled=True,
                global_lock_acquired=lock_acquired,
                global_lock_released=released,
                awaiting_swap_confirmation=False,
                reason="child_already_ledger_settled",
            )

        entry_instr_id, target_instr_id = _resolve_usdc_aave_instrument_ids(db)
        child_meta = _child_metadata(child)
        parent_meta = _parent_metadata(parent)
        notional = _parse_notional_usdc(child_meta, parent_meta)

        swap: PersonWalletSwap | None = None
        if (child.linked_table or "").strip() == LINKED_SWAP_TABLE and child.linked_id is not None:
            swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == child.linked_id).first()
            if swap is None:
                raise BundleB4bBridgeError(
                    "bundle.b4b.linked_swap_not_found",
                    f"swap_id={child.linked_id}",
                )
            _enrich_child_pe_metadata(
                child,
                portfolio_id=parent_ctx["portfolio_id"],
                entry_instrument_id=entry_instr_id,
                target_instrument_id=target_instr_id,
                planned_amount_in=notional,
                swap=swap,
            )
            db.add(child)
            db.flush()
        else:
            swap = _create_fresh_bundle_swap(
                db,
                person_id=person_id,
                portfolio_id=parent_ctx["portfolio_id"],
                parent_intent_id=parent_intent_id,
                child_intent_id=child.id,
                notional_usdc=notional,
                bundle_execution_id=parent.bundle_execution_id,
                plan_hash=parent_ctx["plan_hash"],
                planner_version=parent_ctx["planner_version"],
            )
            if not is_bundle_internal_swap(swap):
                raise BundleB4bBridgeError(
                    "bundle.b4b.swap_not_bundle_internal",
                    "fresh swap sans bundle_execution tag",
                )
            _attach_swap_to_child(
                db,
                child=child,
                swap=swap,
                portfolio_id=parent_ctx["portfolio_id"],
                entry_instrument_id=entry_instr_id,
                target_instrument_id=target_instr_id,
                planned_amount_in=notional,
            )

        if swap is None:
            raise BundleB4bBridgeError(
                "bundle.b4b.missing_swap",
                "swap requis pour B4b",
            )

        if not _swap_is_confirmed(swap):
            return BundleB4bBridgeResult(
                skipped=False,
                idempotent=False,
                completed=False,
                parent_intent_id=parent_intent_id,
                child_intent_id=child.id,
                swap_id=swap.id,
                settled=False,
                global_lock_acquired=lock_acquired,
                global_lock_released=False,
                awaiting_swap_confirmation=True,
                reason="awaiting_swap_confirmation",
            )

        settle_result = settle_bundle_leg_idempotently(
            db,
            child_intent_id=child.id,
        )
        released = _release_global_lock(db, intent_id=parent_intent_id)
        lock_acquired = False

        return BundleB4bBridgeResult(
            skipped=False,
            idempotent=settle_result.idempotent,
            completed=settle_result.settled,
            parent_intent_id=parent_intent_id,
            child_intent_id=child.id,
            swap_id=swap.id,
            settled=settle_result.settled,
            global_lock_acquired=True,
            global_lock_released=released,
            awaiting_swap_confirmation=False,
            reason=settle_result.reason,
        )
    except TransactionInProgress409:
        raise
    except Exception:
        if lock_acquired:
            _release_global_lock(db, intent_id=parent_intent_id)
        raise
