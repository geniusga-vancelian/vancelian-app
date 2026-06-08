"""B3c — Bundle leg settlement handler (child = mini LI.FI · BUY USDC→AAVE Base).

Handler event-driven isolé — flag OFF par défaut.
Settlement child-only : ne charge jamais le parent intent.
Ne remplace pas ``BundleLifiLegService._apply_post_confirmation`` en runtime legacy.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import apply_swap_settlement, swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.allocation_settlement import (
    resolve_allocation_leg_settlement_amounts,
)
from services.portfolio_engine.bundle_execution.bundle_cost_basis import reference_cost_basis_eur
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundle_execution.lifi_base_config import BUNDLE_LIFI_CHAIN_KEY
from services.portfolio_engine.bundle_execution.pe_settlement import (
    BundlePeSettlementError,
    apply_rebalance_buy_atoms,
    swap_confirmed,
)
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler_config import (
    bundle_leg_settlement_handler_enabled,
)
from services.transaction_intents.enums import IntentProductType, IntentRole

BUNDLE_LEG_BUY_FROM_ASSET = "USDC"
BUNDLE_LEG_BUY_TO_ASSET = "AAVE"
BUNDLE_LEG_DIRECTION_BUY = "buy"
BUNDLE_LEG_SETTLEMENT_RECEIPT_KEY = "settlement_receipt_hash"
BUNDLE_LEG_CHILD_REPORT_KEY = "child_report_hash"
BUNDLE_LEG_SETTLEMENT_BLOCK_KEY = "bundle_leg_settlement"
CHILD_REPORT_VERSION = "v1"
HANDLER_VERSION = "bundle_leg_settlement_v1"


class BundleLegSettlementHandlerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class BundleLegSettleResult:
    skipped: bool
    idempotent: bool
    settled: bool
    child_intent_id: UUID | None
    settlement_receipt_hash: str | None
    child_report_hash: str | None
    plan_hash: str | None
    planner_version: str | None
    leg_index: int | None
    reason: str | None = None


def compute_bundle_leg_settlement_receipt_hash(
    *,
    child_intent_id: UUID,
    swap_id: UUID,
    plan_hash: str,
    planner_version: str,
    leg_index: int,
) -> str:
    payload = {
        "child_intent_id": str(child_intent_id),
        "swap_id": str(swap_id),
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "leg_index": leg_index,
        "leg_direction": BUNDLE_LEG_DIRECTION_BUY,
        "from_asset": BUNDLE_LEG_BUY_FROM_ASSET,
        "to_asset": BUNDLE_LEG_BUY_TO_ASSET,
        "handler": HANDLER_VERSION,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def compute_child_report_hash(
    *,
    child_intent_id: UUID,
    settlement_receipt_hash: str,
    plan_hash: str,
    planner_version: str,
    leg_index: int,
) -> str:
    payload = {
        "child_intent_id": str(child_intent_id),
        "settlement_receipt_hash": settlement_receipt_hash,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "leg_index": leg_index,
        "report_version": CHILD_REPORT_VERSION,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _existing_settlement_metadata(intent: TransactionIntent) -> dict[str, Any] | None:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    block = meta.get(BUNDLE_LEG_SETTLEMENT_BLOCK_KEY)
    if isinstance(block, dict) and block.get("settled") is True:
        return block
    return None


def _child_metadata(intent: TransactionIntent) -> dict[str, Any]:
    if isinstance(intent.metadata_json, dict):
        return intent.metadata_json
    return {}


def _validate_child_shape(intent: TransactionIntent) -> dict[str, Any]:
    if intent.product_type != IntentProductType.BUNDLE_LEG.value:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.invalid_product_type",
            f"product_type={intent.product_type}",
        )
    if intent.intent_role != IntentRole.CHILD.value:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.invalid_intent_role",
            f"intent_role={intent.intent_role}",
        )

    meta = _child_metadata(intent)
    plan_hash = str(meta.get("plan_hash") or "").strip()
    planner_version = str(meta.get("planner_version") or "").strip()
    if not plan_hash:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.missing_plan_hash",
            "plan_hash requis sur child metadata",
        )
    if not planner_version:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.missing_planner_version",
            "planner_version requis sur child metadata",
        )

    leg_direction = str(meta.get("leg_direction") or "").strip().lower()
    if leg_direction != BUNDLE_LEG_DIRECTION_BUY:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.sell_not_allowed_b3c",
            f"leg_direction={leg_direction} — B3c BUY ONLY",
        )

    from_asset = str(meta.get("from_asset") or "").strip().upper()
    to_asset = str(meta.get("to_asset") or "").strip().upper()
    if from_asset != BUNDLE_LEG_BUY_FROM_ASSET or to_asset != BUNDLE_LEG_BUY_TO_ASSET:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.invalid_asset_pair_b3c",
            f"Paire {from_asset}→{to_asset} hors scope B3c (USDC→AAVE)",
        )

    portfolio_id_raw = str(meta.get("portfolio_id") or meta.get("bundle_id") or "").strip()
    entry_raw = str(meta.get("entry_instrument_id") or "").strip()
    target_raw = str(meta.get("target_instrument_id") or "").strip()
    if not portfolio_id_raw or not entry_raw or not target_raw:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.missing_pe_context",
            "portfolio_id · entry_instrument_id · target_instrument_id requis",
        )

    leg_index = intent.leg_index
    if leg_index is None:
        leg_index = meta.get("leg_index")
    if leg_index is None:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.missing_leg_index",
            "leg_index requis",
        )

    return {
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "leg_index": int(leg_index),
        "portfolio_id": UUID(portfolio_id_raw),
        "entry_instrument_id": UUID(entry_raw),
        "target_instrument_id": UUID(target_raw),
        "planned_amount_in": meta.get("planned_amount_in"),
    }


def _load_linked_swap(db: Session, child: TransactionIntent) -> PersonWalletSwap:
    if (child.linked_table or "").strip() != "person_wallet_swaps" or child.linked_id is None:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.missing_linked_swap",
            "child sans linked swap person_wallet_swaps",
        )
    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == child.linked_id).first()
    if swap is None:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.linked_swap_not_found",
            f"swap_id={child.linked_id}",
        )
    return swap


def _validate_swap_b3c(swap: PersonWalletSwap) -> None:
    if not is_bundle_internal_swap(swap):
        raise BundleLegSettlementHandlerError(
            "bundle.leg.not_bundle_internal_swap",
            "swap sans bundle_leg_context",
        )
    if (swap.status or "").upper() != SwapSessionStatus.CONFIRMED.value:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.swap_not_confirmed",
            f"status={swap.status}",
        )
    if not str(swap.tx_hash or "").strip():
        raise BundleLegSettlementHandlerError(
            "bundle.leg.missing_tx_hash",
            "tx_hash requis",
        )
    from_asset = str(swap.from_asset or "").upper()
    to_asset = str(swap.to_asset or "").upper()
    if from_asset != BUNDLE_LEG_BUY_FROM_ASSET or to_asset != BUNDLE_LEG_BUY_TO_ASSET:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.swap_asset_pair_mismatch",
            f"swap {from_asset}→{to_asset}",
        )
    from_chain = str(swap.from_chain or "").strip().lower()
    to_chain = str(swap.to_chain or "").strip().lower()
    if from_chain != BUNDLE_LIFI_CHAIN_KEY or to_chain != BUNDLE_LIFI_CHAIN_KEY:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.chain_not_base",
            f"chains {from_chain}/{to_chain}",
        )


def _persist_child_settlement_metadata(
    intent: TransactionIntent,
    *,
    settlement_receipt_hash: str,
    child_report_hash: str,
    plan_hash: str,
    planner_version: str,
    leg_index: int,
    swap_id: UUID,
) -> None:
    meta = dict(intent.metadata_json) if isinstance(intent.metadata_json, dict) else {}
    meta[BUNDLE_LEG_SETTLEMENT_RECEIPT_KEY] = settlement_receipt_hash
    meta[BUNDLE_LEG_CHILD_REPORT_KEY] = child_report_hash
    meta[BUNDLE_LEG_SETTLEMENT_BLOCK_KEY] = {
        "settled": True,
        "settlement_receipt_hash": settlement_receipt_hash,
        "child_report_hash": child_report_hash,
        "plan_hash": plan_hash,
        "planner_version": planner_version,
        "leg_index": leg_index,
        "leg_direction": BUNDLE_LEG_DIRECTION_BUY,
        "swap_id": str(swap_id),
        "settled_at": _utc_now_iso(),
        "phase": "SETTLED",
        "report_version": CHILD_REPORT_VERSION,
    }
    intent.metadata_json = meta


def _apply_buy_leg_pe_atoms(
    db: Session,
    *,
    ctx: dict[str, Any],
    swap: PersonWalletSwap,
) -> None:
    planned_in_raw = ctx.get("planned_amount_in")
    planned_in = (
        Decimal(str(planned_in_raw))
        if planned_in_raw is not None
        else Decimal(str(swap.amount_in))
    )
    settlement = resolve_allocation_leg_settlement_amounts(
        db,
        swap,
        planned_amount_in=planned_in,
        allow_mock_quote_amount=True,
    )
    amount_in = settlement.amount_in
    amount_out = settlement.amount_out
    cost_basis = reference_cost_basis_eur(db, str(swap.from_asset), amount_in)

    apply_rebalance_buy_atoms(
        db,
        portfolio_id=ctx["portfolio_id"],
        instrument_id=ctx["target_instrument_id"],
        entry_instrument_id=ctx["entry_instrument_id"],
        entry_spent=amount_in,
        crypto_received=amount_out,
        cost_basis_eur=cost_basis,
        ledger=None,
    )


def settle_bundle_leg_idempotently(
    db: Session,
    *,
    child_intent_id: UUID,
) -> BundleLegSettleResult:
    """Settle une leg bundle — flag OFF → no-op strict · child_intent_id seul."""
    if not bundle_leg_settlement_handler_enabled():
        return BundleLegSettleResult(
            skipped=True,
            idempotent=False,
            settled=False,
            child_intent_id=child_intent_id,
            settlement_receipt_hash=None,
            child_report_hash=None,
            plan_hash=None,
            planner_version=None,
            leg_index=None,
            reason="bundle_leg_settlement_handler_disabled",
        )

    child = db.query(TransactionIntent).filter(TransactionIntent.id == child_intent_id).first()
    if child is None:
        raise BundleLegSettlementHandlerError(
            "bundle.leg.child_intent_not_found",
            f"child_intent_id={child_intent_id}",
        )

    ctx = _validate_child_shape(child)
    existing = _existing_settlement_metadata(child)
    if existing is not None:
        meta = child.metadata_json if isinstance(child.metadata_json, dict) else {}
        return BundleLegSettleResult(
            skipped=False,
            idempotent=True,
            settled=True,
            child_intent_id=child_intent_id,
            settlement_receipt_hash=str(
                existing.get("settlement_receipt_hash")
                or meta.get(BUNDLE_LEG_SETTLEMENT_RECEIPT_KEY)
                or ""
            )
            or None,
            child_report_hash=str(
                existing.get("child_report_hash") or meta.get(BUNDLE_LEG_CHILD_REPORT_KEY) or ""
            )
            or None,
            plan_hash=str(existing.get("plan_hash") or ctx["plan_hash"]),
            planner_version=str(existing.get("planner_version") or ctx["planner_version"]),
            leg_index=int(existing.get("leg_index") or ctx["leg_index"]),
            reason="already_settled",
        )

    swap = _load_linked_swap(db, child)
    _validate_swap_b3c(swap)

    if not swap_confirmed(swap):
        raise BundleLegSettlementHandlerError(
            "bundle.leg.swap_not_confirmed",
            "swap non confirmé",
        )

    receipt_hash = compute_bundle_leg_settlement_receipt_hash(
        child_intent_id=child_intent_id,
        swap_id=swap.id,
        plan_hash=ctx["plan_hash"],
        planner_version=ctx["planner_version"],
        leg_index=ctx["leg_index"],
    )
    child_report_hash = compute_child_report_hash(
        child_intent_id=child_intent_id,
        settlement_receipt_hash=receipt_hash,
        plan_hash=ctx["plan_hash"],
        planner_version=ctx["planner_version"],
        leg_index=ctx["leg_index"],
    )

    if not swap_settlement_already_applied(swap):
        apply_swap_settlement(db, swap, sync_source="bundle_leg_settlement_handler_b3c")

    if not _pe_atoms_already_applied(swap):
        try:
            _apply_buy_leg_pe_atoms(db, ctx=ctx, swap=swap)
        except BundlePeSettlementError as exc:
            raise BundleLegSettlementHandlerError(
                "bundle.leg.pe_atoms_failed",
                str(exc),
            ) from exc
        _mark_pe_atoms_applied(db, swap, child_intent_id=child_intent_id)

    _persist_child_settlement_metadata(
        child,
        settlement_receipt_hash=receipt_hash,
        child_report_hash=child_report_hash,
        plan_hash=ctx["plan_hash"],
        planner_version=ctx["planner_version"],
        leg_index=ctx["leg_index"],
        swap_id=swap.id,
    )
    db.add(child)
    db.flush()

    return BundleLegSettleResult(
        skipped=False,
        idempotent=False,
        settled=True,
        child_intent_id=child_intent_id,
        settlement_receipt_hash=receipt_hash,
        child_report_hash=child_report_hash,
        plan_hash=ctx["plan_hash"],
        planner_version=ctx["planner_version"],
        leg_index=ctx["leg_index"],
    )


def _pe_atoms_already_applied(swap: PersonWalletSwap) -> bool:
    audit = swap.audit_log
    if isinstance(audit, list):
        return any(
            isinstance(e, dict) and e.get("event") == "bundle_pe_atoms_applied"
            for e in audit
        )
    return False


def _mark_pe_atoms_applied(db: Session, swap: PersonWalletSwap, *, child_intent_id: UUID) -> None:
    from services.lifi.swap_repository import PersonWalletSwapRepository

    PersonWalletSwapRepository().append_audit(
        swap,
        {
            "event": "bundle_pe_atoms_applied",
            "source": "bundle_leg_settlement_handler_b3c",
            "child_intent_id": str(child_intent_id),
        },
    )
    db.add(swap)
    db.flush()
