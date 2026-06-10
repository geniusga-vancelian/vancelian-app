"""Intent transactionnel unifié bundle — dépôt+rebalance et rebalance seul."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent

BUNDLE_TRANSACTION_INTENT_PRODUCT = "bundle_transaction_v1"
BUNDLE_TRANSACTION_FLOW_VERSION = "bundle_transaction_v1"

# Rétrocompat lecture intents / audits en vol
LEGACY_DEPOSIT_INTENT_PRODUCT = "bundle_deposit_v3"
LEGACY_REBALANCE_INTENT_PRODUCT = "bundle_portfolio_rebalance_v1"

BUNDLE_TRANSACTION_OPERATION_DEPOSIT_REBALANCE = "deposit_rebalance"
BUNDLE_TRANSACTION_OPERATION_REBALANCE = "rebalance"

PHASE_FUNDING = "funding"
PHASE_REBALANCING = "rebalancing"
PHASE_TERMINAL = "terminal"

_BUNDLE_TRANSACTION_PRODUCTS = frozenset({
    BUNDLE_TRANSACTION_INTENT_PRODUCT,
    LEGACY_DEPOSIT_INTENT_PRODUCT,
    LEGACY_REBALANCE_INTENT_PRODUCT,
})


def is_bundle_transaction_product(product_type: str | None) -> bool:
    return str(product_type or "") in _BUNDLE_TRANSACTION_PRODUCTS


def create_bundle_transaction_intent(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    transaction_execution_id: UUID,
    operation_type: str,
    phase: str,
    idempotency_suffix: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> TransactionIntent:
    suffix = idempotency_suffix or str(transaction_execution_id)
    metadata: dict[str, Any] = {
        "flow_version": BUNDLE_TRANSACTION_FLOW_VERSION,
        "portfolio_id": str(portfolio_id),
        "transaction_execution_id": str(transaction_execution_id),
        "batch_id": str(transaction_execution_id),
        "phase": phase,
        "operation_type": operation_type,
        "asset_lines": [],
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    intent = TransactionIntent(
        person_id=person_id,
        product_type=BUNDLE_TRANSACTION_INTENT_PRODUCT,
        operation_type=operation_type,
        idempotency_key=f"bundle-transaction-{suffix}",
        status="created",
        metadata_json=metadata,
    )
    db.add(intent)
    db.flush()
    return intent


def set_bundle_transaction_phase(
    intent: TransactionIntent,
    *,
    phase: str,
    extra: dict[str, Any] | None = None,
) -> None:
    meta = dict(intent.metadata_json or {})
    meta["phase"] = phase
    if extra:
        meta.update(extra)
    intent.metadata_json = meta


def sync_bundle_transaction_rebalancing(
    intent: TransactionIntent,
    *,
    result: dict[str, Any],
    asset_lines: list[dict[str, str]] | None = None,
) -> None:
    v3_status = str(result.get("v3_status") or "")
    meta = dict(intent.metadata_json or {})
    meta.update({
        "phase": PHASE_TERMINAL if v3_status in {
            "COMPLETED",
            "COMPLETED_WITH_RESIDUAL_CASH",
            "FAILED",
            "NO_ACTION",
        } else PHASE_REBALANCING,
        "v3_status": result.get("v3_status"),
        "rebalance_execution_id": result.get("rebalance_execution_id"),
        "batch_id": result.get("batch_id") or meta.get("batch_id"),
        "plan_hash": result.get("plan_hash") or meta.get("plan_hash"),
        "snapshot_hash": result.get("snapshot_hash") or meta.get("snapshot_hash"),
    })
    if asset_lines is not None:
        meta["asset_lines"] = asset_lines
    intent.metadata_json = meta
    if v3_status:
        intent.status = v3_status.lower()
    elif result.get("status"):
        intent.status = str(result.get("status")).lower()


def find_bundle_transaction_intent_by_rebalance_execution_id(
    db: Session,
    *,
    rebalance_execution_id: str,
) -> TransactionIntent | None:
    if not rebalance_execution_id:
        return None
    candidates = (
        db.query(TransactionIntent)
        .filter(TransactionIntent.product_type.in_(_BUNDLE_TRANSACTION_PRODUCTS))
        .order_by(TransactionIntent.created_at.desc())
        .limit(30)
        .all()
    )
    for row in candidates:
        meta = row.metadata_json or {}
        if str(meta.get("rebalance_execution_id") or "") == rebalance_execution_id:
            return row
    return None
