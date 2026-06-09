"""Rééquilibrage portefeuille bundle — intent transactionnel + drift V3.

Remplace la reprise legacy LI.FI (« Reprendre l'investissement ») par un flux
sell-then-buy en devise d'entrée (USDC/EURC), min 1 USDC, même rail swap LI.FI.
Acquiert le même guard ``portfolio_financial_operations`` que bundle invest.
"""
from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundles.bundle_invest_lock import (
    clear_invest_lock,
    get_active_invest_lock_for_portfolio,
    release_invest_lock,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
    is_v3_deposit_batch,
)
from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
from services.portfolio_engine.bundles.rebalance_executor import (
    BundleRebalanceExecutorError,
    execute_v3_bundle_rebalance,
)
from services.portfolio_engine.bundles.rebalance_planner import plan_bundle_rebalance_from_drift
from services.portfolio_engine.financial_operations.wiring import (
    acquire_bundle_rebalance_v3_portfolio_operation,
    release_bundle_rebalance_v3_portfolio_operation,
)
from services.portfolio_engine.hardening.audit_service import AuditService
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

REBALANCE_PORTFOLIO_INTENT_PRODUCT = "bundle_portfolio_rebalance_v1"
REBALANCE_PORTFOLIO_FLOW_VERSION = "bundle_portfolio_rebalance_v1"

PORTFOLIO_REBALANCING_REQUIRED_CODE = "portfolio_rebalancing_required"
CASH_REBALANCE_REQUIRED_CODE = "cash_rebalance_required"

_TERMINAL_V3_STATUSES = frozenset({
    "COMPLETED",
    "COMPLETED_WITH_RESIDUAL_CASH",
    "FAILED",
    "NO_ACTION",
})

_PENDING_SWAP_STATUSES = frozenset({
    SwapSessionStatus.AWAITING_SIGNATURE.value,
    SwapSessionStatus.QUOTE_RECEIVED.value,
    SwapSessionStatus.PENDING.value,
})


class RebalancingPortfolioError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def portfolio_rebalancing_required_body() -> dict[str, Any]:
    return {
        "status": PORTFOLIO_REBALANCING_REQUIRED_CODE,
        "error_code": PORTFOLIO_REBALANCING_REQUIRED_CODE,
        "message": (
            "Ce portefeuille doit être rééquilibré via le flux portefeuille "
            "(POST /bundle/{portfolio_id}/rebalancing)."
        ),
        "action": "portfolio_rebalancing",
    }


def cash_rebalance_required_body(*, batch_id: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "status": CASH_REBALANCE_REQUIRED_CODE,
        "error_code": CASH_REBALANCE_REQUIRED_CODE,
        "message": (
            "La reprise invest legacy est dépréciée. Utilisez le rééquilibrage portefeuille "
            "pour déployer le cash leg et abandonner le batch bloqué."
        ),
        "action": "portfolio_rebalancing",
    }
    if batch_id:
        body["batch_id"] = batch_id
    return body


def should_use_portfolio_rebalancing(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> bool:
    """True si legacy /rebalance ou /invest/resume doit rediriger vers /rebalancing."""
    lock = get_active_invest_lock_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if lock is not None:
        batch_id = str(lock.get("batch_id") or "").strip()
        if batch_id and not is_v3_deposit_batch(
            db, portfolio_id=portfolio_id, batch_id=batch_id,
        ):
            return True

    preview = preview_rebalancing_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    plan_status = str((preview.get("rebalance_plan") or {}).get("status") or "")
    return plan_status == "ok"


def _resolve_person_id(db: Session, client_id: UUID) -> UUID | None:
    from services.portfolio_engine.clients.models import Client

    row = db.query(Client).filter(Client.id == client_id).first()
    return row.person_id if row is not None else None


def _would_abandon_legacy_lock(
    db: Session,
    *,
    portfolio_id: UUID,
    lock: dict[str, Any] | None,
) -> bool:
    if lock is None:
        return False
    batch_id = str(lock.get("batch_id") or "").strip()
    if not batch_id:
        return False
    return not is_v3_deposit_batch(db, portfolio_id=portfolio_id, batch_id=batch_id)


def _expire_pending_swaps_for_legacy_batch(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> list[str]:
    expired: list[str] = []
    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status.in_(list(_PENDING_SWAP_STATUSES)),
        )
        .all()
    )
    portfolio_key = str(portfolio_id)
    for swap in swaps:
        ctx = bundle_context_from_swap_audit(swap) or {}
        if str(ctx.get("portfolio_id") or "") != portfolio_key:
            continue
        if str(ctx.get("batch_id") or "") != batch_id:
            continue
        swap.status = SwapSessionStatus.EXPIRED.value
        db.add(swap)
        expired.append(str(swap.id))
    return expired


def abandon_legacy_invest_lock_for_rebalancing(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> dict[str, Any]:
    """Abandonne un batch invest legacy bloqué (signature pending) avant rééquilibrage."""
    lock = get_active_invest_lock_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if lock is None:
        return {"abandoned": False, "reason": "no_active_lock"}

    batch_id = str(lock.get("batch_id") or "").strip()
    if not batch_id:
        return {"abandoned": False, "reason": "empty_batch_id"}

    if is_v3_deposit_batch(db, portfolio_id=portfolio_id, batch_id=batch_id):
        return {"abandoned": False, "reason": "v3_deposit_batch", "batch_id": batch_id}

    person_id = _resolve_person_id(db, client_id)
    expired_swap_ids: list[str] = []
    if person_id is not None:
        expired_swap_ids = _expire_pending_swaps_for_legacy_batch(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )

    release_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        terminal_status="expired",
    )
    clear_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )

    AuditService.log_success(
        db,
        entity_type="portfolio",
        entity_id=str(portfolio_id),
        action="bundle.rebalancing_abandon_legacy_invest_lock",
        actor_id=f"rebalancing-portfolio:{batch_id}",
        metadata={
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "batch_id": batch_id,
            "expired_swap_ids": expired_swap_ids,
        },
    )
    return {
        "abandoned": True,
        "batch_id": batch_id,
        "expired_swap_ids": expired_swap_ids,
    }


def _create_rebalance_intent(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    execution_id: UUID,
    plan_hash: str,
    snapshot_hash: str,
) -> TransactionIntent:
    intent = TransactionIntent(
        person_id=person_id,
        product_type=REBALANCE_PORTFOLIO_INTENT_PRODUCT,
        operation_type="rebalance",
        idempotency_key=f"portfolio-rebalance-{execution_id}",
        status="created",
        metadata_json={
            "flow_version": REBALANCE_PORTFOLIO_FLOW_VERSION,
            "portfolio_id": str(portfolio_id),
            "rebalance_execution_id": str(execution_id),
            "batch_id": str(execution_id),
            "plan_hash": plan_hash,
            "snapshot_hash": snapshot_hash,
            "asset_lines": [],
        },
    )
    db.add(intent)
    db.flush()
    return intent


def _asset_lines_from_plan(plan: dict[str, Any]) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    for leg in plan.get("sell_plan") or []:
        lines.append({
            "asset": str(leg.get("asset") or ""),
            "action": "sell",
            "amount_entry": str(leg.get("amount_usdc") or "0"),
            "status": "planned",
        })
    for leg in plan.get("buy_plan") or []:
        lines.append({
            "asset": str(leg.get("asset") or ""),
            "action": "buy",
            "amount_entry": str(leg.get("amount_usdc") or "0"),
            "status": "planned",
        })
    return lines


def _asset_lines_from_execution(result: dict[str, Any]) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    for bucket, action in (("sell_results", "sell"), ("buy_results", "buy")):
        for leg in result.get(bucket) or []:
            if isinstance(leg, dict):
                asset = str(leg.get("asset") or "")
                status = str(leg.get("status") or "unknown")
                amount = str(leg.get("amount_usdc") or leg.get("amount_entry") or "")
            else:
                asset = str(getattr(leg, "asset", "") or "")
                status = str(getattr(leg, "status", "unknown") or "unknown")
                amount = str(getattr(leg, "amount_usdc", "") or "")
            lines.append({
                "asset": asset,
                "action": action,
                "amount_entry": amount,
                "status": status,
            })
    return lines


def _compute_drift_and_plan(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> tuple[dict[str, Any], dict[str, Any]]:
    drift = compute_bundle_drift_snapshot(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    plan = plan_bundle_rebalance_from_drift(drift)
    return drift, plan


def _active_financial_operation_blocker(
    db: Session,
    *,
    portfolio_id: UUID,
) -> dict[str, Any] | None:
    from services.portfolio_engine.financial_operations.service import (
        find_active_portfolio_financial_operation,
    )

    active = find_active_portfolio_financial_operation(db, portfolio_id=portfolio_id)
    if active is None:
        return None
    return {
        "code": "portfolio_financial_operation_in_progress",
        "operation_type": str(active.operation_type),
        "execution_id": str(active.execution_id),
    }


def preview_rebalancing_portfolio(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> dict[str, Any]:
    drift, plan = _compute_drift_and_plan(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    return {
        "flow": REBALANCE_PORTFOLIO_FLOW_VERSION,
        "portfolio_id": str(portfolio_id),
        "drift_snapshot": drift,
        "rebalance_plan": plan,
        "asset_lines": _asset_lines_from_plan(plan),
        "status": plan.get("status") or "ok",
    }


def preflight_rebalancing_portfolio(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> dict[str, Any]:
    """Read-only — drift, plan, blockers, sans abandon lock ni exécution."""
    lock = get_active_invest_lock_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    drift, plan = _compute_drift_and_plan(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    plan_status = str(plan.get("status") or "no_action")

    blockers: list[dict[str, Any]] = []
    fin_blocker = _active_financial_operation_blocker(db, portfolio_id=portfolio_id)
    if fin_blocker is not None:
        blockers.append(fin_blocker)

    if lock is not None:
        batch_id = str(lock.get("batch_id") or "").strip()
        if batch_id and is_v3_deposit_batch(db, portfolio_id=portfolio_id, batch_id=batch_id):
            blockers.append({
                "code": "v3_deposit_batch_in_progress",
                "batch_id": batch_id,
            })

    can_execute = plan_status == "ok" and not blockers

    return {
        "flow": REBALANCE_PORTFOLIO_FLOW_VERSION,
        "portfolio_id": str(portfolio_id),
        "can_execute": can_execute,
        "blockers": blockers,
        "would_abandon_legacy_lock": _would_abandon_legacy_lock(
            db, portfolio_id=portfolio_id, lock=lock,
        ),
        "legacy_lock": dict(lock) if lock is not None else None,
        "drift_snapshot": drift,
        "rebalance_plan": plan,
        "asset_lines": _asset_lines_from_plan(plan),
        "status": plan_status,
    }


def rebalancing_portfolio(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    trigger: str = "manual",
) -> dict[str, Any]:
    """Rééquilibrage nominal : guard PE → abandon lock legacy → drift → sell → buy."""
    execution_id = uuid.uuid4()

    acquire_bundle_rebalance_v3_portfolio_operation(
        db,
        portfolio_id=portfolio_id,
        execution_id=execution_id,
    )

    def _release_guard(*, failed: bool = False) -> None:
        release_bundle_rebalance_v3_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            execution_id=execution_id,
            failed=failed,
        )

    person_id = _resolve_person_id(db, client_id)
    if person_id is None:
        _release_guard(failed=True)
        raise RebalancingPortfolioError("client_has_no_person_id", "client_has_no_person_id")

    abandoned = abandon_legacy_invest_lock_for_rebalancing(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if (
        not abandoned.get("abandoned")
        and abandoned.get("reason") == "v3_deposit_batch"
    ):
        _release_guard(failed=True)
        raise RebalancingPortfolioError(
            "v3_deposit_batch_in_progress",
            "v3_deposit_batch_in_progress",
        )

    drift, plan = _compute_drift_and_plan(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    plan_hash = str(plan.get("plan_hash") or "")
    snapshot_hash = str(plan.get("snapshot_hash") or drift.get("snapshot_hash") or "")

    intent = _create_rebalance_intent(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        execution_id=execution_id,
        plan_hash=plan_hash,
        snapshot_hash=snapshot_hash,
    )

    try:
        result = execute_v3_bundle_rebalance(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            drift_rebalance_plan=plan,
            trigger=trigger,  # type: ignore[arg-type]
            plan_hash=plan_hash or None,
        )
    except BundleRebalanceExecutorError as exc:
        _release_guard(failed=True)
        intent.status = "failed"
        meta = dict(intent.metadata_json or {})
        meta["error"] = str(exc)
        intent.metadata_json = meta
        db.add(intent)
        raise RebalancingPortfolioError("rebalancing_execution_failed", str(exc)) from exc

    v3_status = str(result.get("v3_status") or "")
    if v3_status in _TERMINAL_V3_STATUSES:
        _release_guard(failed=(v3_status == "FAILED"))

    asset_lines = _asset_lines_from_execution(result)
    intent.status = str(result.get("v3_status") or result.get("status") or "completed").lower()
    meta = dict(intent.metadata_json or {})
    meta.update({
        "v3_status": result.get("v3_status"),
        "rebalance_execution_id": result.get("rebalance_execution_id"),
        "batch_id": result.get("batch_id"),
        "asset_lines": asset_lines,
        "legacy_lock_abandoned": abandoned,
        "financial_operation_execution_id": str(execution_id),
    })
    intent.metadata_json = meta
    db.add(intent)

    return {
        "flow": REBALANCE_PORTFOLIO_FLOW_VERSION,
        "intent_id": str(intent.id),
        "financial_operation_execution_id": str(execution_id),
        "legacy_lock_abandoned": abandoned,
        "drift_snapshot": drift,
        "rebalance_plan": plan,
        "asset_lines": asset_lines,
        **result,
    }
