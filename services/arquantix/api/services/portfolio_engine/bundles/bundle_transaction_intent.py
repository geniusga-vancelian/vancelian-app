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


_TERMINAL_V3 = frozenset({
    "COMPLETED",
    "COMPLETED_WITH_RESIDUAL_CASH",
    "FAILED",
    "NO_ACTION",
})

_TERMINAL_INTENT_STATUS = frozenset({
    "failed",
    "completed",
    "completed_with_residual_cash",
    "confirmed",
    "no_action",
})


def intent_marked_running(row: TransactionIntent) -> bool:
    """True si l'intent est encore étiqueté RUNNING côté DB."""
    meta = row.metadata_json or {}
    v3 = str(meta.get("v3_status") or "").upper()
    status = str(row.status or "").lower()
    if v3 in _TERMINAL_V3 or status in _TERMINAL_INTENT_STATUS:
        return False
    return v3 == "RUNNING" or status in ("running", "created", "queued")


def _terminal_payload_for_orphan_intent(
    db: Session,
    *,
    portfolio_id: str,
    batch_id: str,
) -> dict[str, Any]:
    from services.portfolio_engine.bundles.rebalance_executor import (
        ACTION_V3_TERMINAL,
        ENTITY_TYPE_V3_REBALANCE,
    )
    from services.portfolio_engine.hardening.audit_models import AuditEvent

    if batch_id:
        rows = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
                AuditEvent.action == ACTION_V3_TERMINAL,
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(100)
            .all()
        )
        for row in rows:
            meta = row.metadata_ or {}
            if str(meta.get("portfolio_id") or "") != portfolio_id:
                continue
            audit_batch = str(
                meta.get("batch_id") or meta.get("rebalance_execution_id") or "",
            )
            if audit_batch == batch_id:
                return dict(meta)
    return {
        "v3_status": "FAILED",
        "rebalance_execution_id": batch_id or None,
        "batch_id": batch_id or None,
        "portfolio_id": portfolio_id,
        "orphan_intent_closed": True,
        "orphan_reason": "no_running_v3_audit",
    }


def find_running_bundle_transaction_intent_for_portfolio(
    db: Session,
    *,
    portfolio_id: UUID | str,
) -> TransactionIntent | None:
    """Intent bundle encore RUNNING — uniquement si réellement non terminal."""
    pid = str(portfolio_id)
    rows = (
        db.query(TransactionIntent)
        .filter(TransactionIntent.product_type.in_(_BUNDLE_TRANSACTION_PRODUCTS))
        .order_by(TransactionIntent.created_at.desc())
        .limit(30)
        .all()
    )
    for row in rows:
        meta = row.metadata_json or {}
        if str(meta.get("portfolio_id") or "") != pid:
            continue
        if intent_marked_running(row):
            return row
    return None


def close_orphan_bundle_transaction_intents_for_portfolio(
    db: Session,
    *,
    portfolio_id: UUID | str,
) -> list[dict[str, Any]]:
    """Clôture tous les intents bundle RUNNING sans exécution V3 RUNNING correspondante."""
    from services.portfolio_engine.bundles.rebalance_executor import (
        find_running_v3_rebalance_execution,
    )

    pid = str(portfolio_id)
    if find_running_v3_rebalance_execution(db, portfolio_id=pid) is not None:
        return []

    closed: list[dict[str, Any]] = []
    rows = (
        db.query(TransactionIntent)
        .filter(TransactionIntent.product_type.in_(_BUNDLE_TRANSACTION_PRODUCTS))
        .order_by(TransactionIntent.created_at.desc())
        .limit(50)
        .all()
    )
    for row in rows:
        meta = row.metadata_json or {}
        if str(meta.get("portfolio_id") or "") != pid:
            continue
        if not intent_marked_running(row):
            continue
        batch_id = str(
            meta.get("rebalance_execution_id") or meta.get("batch_id") or "",
        ).strip()
        terminal = _terminal_payload_for_orphan_intent(
            db, portfolio_id=pid, batch_id=batch_id,
        )
        sync_bundle_transaction_rebalancing(row, result=terminal)
        if str(terminal.get("v3_status") or "") in _TERMINAL_V3:
            from services.portfolio_engine.bundles.bundle_transaction_global_lock import (
                release_bundle_transaction_global_lock_on_v3_terminal,
            )

            release_bundle_transaction_global_lock_on_v3_terminal(
                db,
                intent_id=row.id,
                v3_status=str(terminal.get("v3_status") or "FAILED"),
            )
        db.add(row)
        closed.append({
            "intent_id": str(row.id),
            "v3_status": terminal.get("v3_status"),
            "batch_id": batch_id or None,
        })
    return closed


def finalize_bundle_transaction_after_v3_terminal(
    db: Session,
    *,
    portfolio_id: UUID | str,
    terminal: dict[str, Any],
) -> TransactionIntent | None:
    """Sync intent + libère lock global après clôture V3 (reconcile / terminalize)."""
    from services.portfolio_engine.bundles.bundle_transaction_global_lock import (
        release_bundle_transaction_global_lock_on_v3_terminal,
    )

    v3_status = str(terminal.get("v3_status") or "")
    exec_id = str(terminal.get("rebalance_execution_id") or terminal.get("batch_id") or "")
    intent = find_bundle_transaction_intent_by_rebalance_execution_id(
        db,
        rebalance_execution_id=exec_id,
    )
    if intent is None:
        intent = find_running_bundle_transaction_intent_for_portfolio(
            db, portfolio_id=portfolio_id,
        )
    if intent is None:
        return None

    sync_bundle_transaction_rebalancing(intent, result=terminal)
    if v3_status in _TERMINAL_V3:
        release_bundle_transaction_global_lock_on_v3_terminal(
            db,
            intent_id=intent.id,
            v3_status=v3_status,
        )
    db.add(intent)
    return intent


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
