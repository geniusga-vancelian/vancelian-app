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
    close_stale_bundle_invest_intents_for_portfolio,
    find_active_bundle_batch_ids_for_portfolio,
    get_active_invest_lock_for_portfolio,
    release_invest_lock,
)
from services.portfolio_engine.bundles.bundle_transaction_global_lock import (
    acquire_bundle_transaction_global_lock_or_raise,
    release_bundle_transaction_global_lock_on_v3_terminal,
)
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    BUNDLE_TRANSACTION_FLOW_VERSION,
    BUNDLE_TRANSACTION_OPERATION_REBALANCE,
    LEGACY_REBALANCE_INTENT_PRODUCT,
    PHASE_REBALANCING,
    create_bundle_transaction_intent,
    find_bundle_transaction_intent_by_rebalance_execution_id,
    sync_bundle_transaction_rebalancing,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
    is_v3_deposit_batch,
)
from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
from services.portfolio_engine.bundles.rebalance_executor import (
    BundleRebalanceExecutorError,
    execute_v3_bundle_rebalance,
    find_latest_terminal_v3_rebalance_for_portfolio,
    find_running_v3_rebalance_execution,
    force_terminalize_running_v3_rebalance_on_plan_drift,
    reconcile_running_v3_rebalance_execution,
    resume_v3_bundle_rebalance_execution,
)
from services.portfolio_engine.bundles.rebalance_planner import plan_bundle_rebalance_from_drift
from services.portfolio_engine.financial_operations.wiring import (
    acquire_bundle_transaction_v3_portfolio_operation,
    release_active_bundle_portfolio_operation,
    release_bundle_transaction_v3_portfolio_operation,
)
from services.portfolio_engine.hardening.audit_service import AuditService
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

REBALANCE_PORTFOLIO_INTENT_PRODUCT = LEGACY_REBALANCE_INTENT_PRODUCT
REBALANCE_PORTFOLIO_FLOW_VERSION = BUNDLE_TRANSACTION_FLOW_VERSION

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
    batch_id, source = _resolve_legacy_batch_for_rebalancing(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if batch_id and source != "ambiguous_batches" and not is_v3_deposit_batch(
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


def _resolve_legacy_batch_for_rebalancing(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> tuple[str | None, str]:
    """Résout le batch legacy — metadata lock OU batch reconstitué depuis swaps pending."""
    lock = get_active_invest_lock_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if lock is not None:
        batch_id = str(lock.get("batch_id") or "").strip()
        if batch_id:
            return batch_id, "metadata_lock"

    active_batches = find_active_bundle_batch_ids_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if len(active_batches) == 1:
        return active_batches[0], "recovered_pending_batch"
    if len(active_batches) > 1:
        return None, "ambiguous_batches"
    return None, "no_active_lock"


def _would_abandon_legacy_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> bool:
    batch_id, reason = _resolve_legacy_batch_for_rebalancing(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if not batch_id or reason == "ambiguous_batches":
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
    """Abandonne un batch invest legacy bloqué (metadata lock ou swap CBETH pending)."""
    batch_id, source = _resolve_legacy_batch_for_rebalancing(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if not batch_id:
        return {"abandoned": False, "reason": source}

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

    lock = get_active_invest_lock_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if lock is not None and str(lock.get("batch_id") or "").strip() == batch_id:
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
            "source": source,
            "expired_swap_ids": expired_swap_ids,
        },
    )
    return {
        "abandoned": True,
        "batch_id": batch_id,
        "source": source,
        "expired_swap_ids": expired_swap_ids,
    }


def _asset_lines_from_plan(plan: dict[str, Any]) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    entry_asset = str(plan.get("entry_asset") or "USDC")

    def _append_line(leg: dict[str, Any], *, action: str) -> None:
        row: dict[str, str] = {
            "asset": str(leg.get("asset") or ""),
            "action": action,
            "amount_entry": str(leg.get("amount_usdc") or "0"),
            "entry_asset": entry_asset,
            "status": "planned",
        }
        for field in (
            "current_value_usdc",
            "target_value_usdc",
            "price_usdc",
            "amount_crypto",
            "funded_by",
        ):
            value = leg.get(field)
            if value is not None and str(value) != "":
                row[field] = str(value)
        lines.append(row)

    for leg in plan.get("sell_plan") or []:
        _append_line(leg, action="sell")
    for leg in plan.get("buy_plan") or []:
        _append_line(leg, action="buy")
    return lines


def _asset_lines_from_running_snapshot(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    """Fusionne plan + résultats partiels pour l'UI (worker en cours)."""
    lines: list[dict[str, str]] = []
    entry_asset = str(snapshot.get("entry_asset") or "USDC")

    def _append_from_bucket(
        *,
        results_key: str,
        plan_key: str,
        action: str,
    ) -> None:
        results = {
            str(row.get("asset") or ""): row
            for row in (snapshot.get(results_key) or [])
            if isinstance(row, dict)
        }
        plan_legs = snapshot.get(plan_key) or []
        if plan_legs:
            for leg in plan_legs:
                if not isinstance(leg, dict):
                    continue
                asset = str(leg.get("asset") or "")
                result = results.get(asset) or {}
                row: dict[str, str] = {
                    "asset": asset,
                    "action": action,
                    "amount_entry": str(
                        result.get("amount_usdc") or leg.get("amount_usdc") or "0",
                    ),
                    "entry_asset": entry_asset,
                    "status": str(result.get("status") or "planned"),
                }
                for field in (
                    "current_value_usdc",
                    "target_value_usdc",
                    "price_usdc",
                    "amount_crypto",
                    "funded_by",
                    "swap_id",
                ):
                    value = result.get(field) if field in result else leg.get(field)
                    if value is not None and str(value) != "":
                        row[field] = str(value)
                if action == "sell" and result.get("amount_in"):
                    row["amount_crypto"] = str(result["amount_in"])
                elif action == "buy" and result.get("estimated_receive"):
                    row["amount_crypto"] = str(result["estimated_receive"])
                lines.append(row)
            return
        for row in snapshot.get(results_key) or []:
            if not isinstance(row, dict):
                continue
            lines.append({
                "asset": str(row.get("asset") or ""),
                "action": action,
                "amount_entry": str(row.get("amount_usdc") or "0"),
                "entry_asset": entry_asset,
                "status": str(row.get("status") or "unknown"),
            })

    _append_from_bucket(results_key="sell_results", plan_key="sell_plan", action="sell")
    _append_from_bucket(results_key="buy_results", plan_key="buy_plan", action="buy")
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


def _close_stale_bundle_operation_intents(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> list[dict[str, Any]]:
    """Clôture intents bundle zombies (rebalance V3 orphelins + invest stale)."""
    from services.portfolio_engine.bundles.bundle_transaction_intent import (
        close_orphan_bundle_transaction_intents_for_portfolio,
    )

    actions: list[dict[str, Any]] = []
    for closed in close_orphan_bundle_transaction_intents_for_portfolio(
        db, portfolio_id=portfolio_id,
    ):
        actions.append({"kind": "orphan_intent_closed", **closed})

    person_id = _resolve_person_id(db, client_id)
    if person_id is not None:
        from services.portfolio_engine.bundles.bundle_invest_lock import (
            close_orphan_bundle_invest_intents_after_v3_terminal,
        )

        for closed in close_orphan_bundle_invest_intents_after_v3_terminal(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
        ):
            actions.append({"kind": "orphan_invest_after_v3_terminal", **closed})
        for closed in close_stale_bundle_invest_intents_for_portfolio(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
        ):
            actions.append({"kind": "stale_invest_intent_closed", **closed})
    return actions


def reconcile_stale_bundle_portfolio_state(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    force_signable_v3_close: bool = False,
) -> dict[str, Any]:
    """Nettoie zombies bundle (V3, lock legacy, intent) — appelé au chargement page wallet."""
    from services.portfolio_engine.bundles.bundle_invest_lock import (
        _reconcile_stale_intent_legs_for_batch,
        reconcile_or_expire_idle_invest_lock,
    )
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    pid = str(portfolio_id)
    actions: list[dict[str, Any]] = []

    portfolio = BundleOrchestrator._load_and_validate_portfolio(
        db, portfolio_id, client_id,
    )
    _drift, current_plan = _compute_drift_and_plan(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )

    if force_signable_v3_close:
        from services.portfolio_engine.bundles.rebalance_executor import (
            force_close_stale_signable_v3_rebalance,
        )

        signable_closed = force_close_stale_signable_v3_rebalance(
            db,
            portfolio_id=pid,
            client_id=client_id,
            drift_rebalance_plan=current_plan,
            reason="reconcile_stale_force_signable",
            max_age_minutes=0,
        )
        if signable_closed is not None:
            actions.append({
                "kind": "v3_signable_force_closed",
                "v3_status": signable_closed.get("v3_status"),
            })

    terminal = reconcile_running_v3_rebalance_execution(
        db,
        portfolio_id=pid,
        client_id=client_id,
        drift_rebalance_plan=current_plan,
        auto_progress=False,
    )
    if terminal is not None:
        actions.append({
            "kind": "v3_reconcile_terminal",
            "v3_status": terminal.get("v3_status"),
        })

    actions.extend(
        _close_stale_bundle_operation_intents(
            db, client_id=client_id, portfolio_id=portfolio_id,
        ),
    )

    person_id = _resolve_person_id(db, client_id)
    batch_id, source = _resolve_legacy_batch_for_rebalancing(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if (
        person_id is not None
        and batch_id
        and source != "ambiguous_batches"
        and not is_v3_deposit_batch(db, portfolio_id=portfolio_id, batch_id=batch_id)
    ):
        _reconcile_stale_intent_legs_for_batch(
            db,
            person_id=person_id,
            bundle_id=pid,
            batch_id=batch_id,
        )
        actions.append({"kind": "legacy_intent_legs_reconciled", "batch_id": batch_id})
        if _would_abandon_legacy_lock(db, client_id=client_id, portfolio_id=portfolio_id):
            abandoned = abandon_legacy_invest_lock_for_rebalancing(
                db, client_id=client_id, portfolio_id=portfolio_id,
            )
            if abandoned.get("abandoned"):
                actions.append({"kind": "legacy_lock_abandoned", **abandoned})

    if reconcile_or_expire_idle_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        portfolio=portfolio,
    ):
        actions.append({"kind": "invest_lock_reconciled"})

    active = get_active_bundle_operation(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    return {
        "portfolio_id": pid,
        "reconciled": True,
        "actions": actions,
        "active_operation": active,
    }


def get_active_bundle_operation(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> dict[str, Any]:
    """Opération bundle en cours (dépôt V3 ou rééquilibrage) — lecture seule pour reprise UI."""
    pid = str(portfolio_id)
    drift, current_plan = _compute_drift_and_plan(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    reconcile_running_v3_rebalance_execution(
        db,
        portfolio_id=pid,
        client_id=client_id,
        drift_rebalance_plan=current_plan,
        auto_progress=False,
    )
    running = find_running_v3_rebalance_execution(db, portfolio_id=pid)

    if running is not None:
        trigger = str(running.get("trigger") or "manual")
        operation_type = (
            "v3_deposit_rebalance" if trigger == "deposit" else "portfolio_rebalancing"
        )
        asset_lines = _asset_lines_from_running_snapshot(running)
        if not asset_lines:
            asset_lines = _asset_lines_from_execution(running)

        running_plan_hash = str(running.get("plan_hash") or "")
        current_plan_hash = str(current_plan.get("plan_hash") or "")
        plan_stale = bool(
            running_plan_hash
            and current_plan_hash
            and running_plan_hash != current_plan_hash
        )
        current_asset_lines = (
            _asset_lines_from_plan(current_plan) if plan_stale else None
        )

        return {
            "status": "active",
            "operation_type": operation_type,
            "portfolio_id": pid,
            "v3_status": str(running.get("v3_status") or "RUNNING"),
            "rebalance_execution_id": running.get("rebalance_execution_id"),
            "batch_id": running.get("batch_id"),
            "trigger": trigger,
            "asset_lines": asset_lines,
            "sell_results": running.get("sell_results") or [],
            "buy_results": running.get("buy_results") or [],
            "sell_plan": running.get("sell_plan") or [],
            "buy_plan": running.get("buy_plan") or [],
            "planning_mode": running.get("planning_mode"),
            "plan_hash": running_plan_hash or None,
            "current_plan_hash": current_plan_hash or None,
            "plan_stale": plan_stale,
            "current_asset_lines": current_asset_lines,
            "current_planning_mode": current_plan.get("planning_mode"),
        }

    lock = get_active_invest_lock_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if lock is not None:
        batch_id = str(lock.get("batch_id") or "").strip()
        if batch_id and is_v3_deposit_batch(
            db, portfolio_id=portfolio_id, batch_id=batch_id,
        ):
            return {
                "status": "active",
                "operation_type": "v3_deposit_rebalance",
                "portfolio_id": pid,
                "v3_status": "QUEUED",
                "batch_id": batch_id,
                "trigger": "deposit",
                "funding_amount": str(
                    lock.get("funding_amount")
                    or lock.get("planned_entry_total")
                    or "",
                ),
                "asset_lines": [],
                "message": "Dépôt enregistré — rééquilibrage en cours de démarrage.",
            }

    return {"status": "none", "portfolio_id": pid}


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
    legacy_batch_id, legacy_batch_source = _resolve_legacy_batch_for_rebalancing(
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

    if legacy_batch_source == "ambiguous_batches":
        blockers.append({"code": "ambiguous_legacy_batches"})

    if legacy_batch_id and is_v3_deposit_batch(
        db, portfolio_id=portfolio_id, batch_id=legacy_batch_id,
    ):
        blockers.append({
            "code": "v3_deposit_batch_in_progress",
            "batch_id": legacy_batch_id,
        })

    can_execute = plan_status == "ok" and not blockers

    return {
        "flow": REBALANCE_PORTFOLIO_FLOW_VERSION,
        "portfolio_id": str(portfolio_id),
        "can_execute": can_execute,
        "blockers": blockers,
        "would_abandon_legacy_lock": _would_abandon_legacy_lock(
            db, client_id=client_id, portfolio_id=portfolio_id,
        ),
        "legacy_batch_id": legacy_batch_id,
        "legacy_batch_source": legacy_batch_source if legacy_batch_id else None,
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

    acquire_bundle_transaction_v3_portfolio_operation(
        db,
        portfolio_id=portfolio_id,
        execution_id=execution_id,
    )

    def _release_guard(*, failed: bool = False) -> None:
        release_bundle_transaction_v3_portfolio_operation(
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

    intent = create_bundle_transaction_intent(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        transaction_execution_id=execution_id,
        operation_type=BUNDLE_TRANSACTION_OPERATION_REBALANCE,
        phase=PHASE_REBALANCING,
        idempotency_suffix=f"rebalance-{execution_id}",
        extra_metadata={
            "rebalance_execution_id": str(execution_id),
            "plan_hash": plan_hash,
            "snapshot_hash": snapshot_hash,
        },
    )
    acquire_bundle_transaction_global_lock_or_raise(
        db,
        person_id=person_id,
        intent_id=intent.id,
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
        release_bundle_transaction_global_lock_on_v3_terminal(
            db,
            intent_id=intent.id,
            v3_status=v3_status,
        )

    asset_lines = _asset_lines_from_execution(result)
    sync_bundle_transaction_rebalancing(intent, result=result, asset_lines=asset_lines)
    meta = dict(intent.metadata_json or {})
    meta.update({
        "legacy_lock_abandoned": abandoned,
        "financial_operation_execution_id": str(execution_id),
    })
    intent.metadata_json = meta
    db.add(intent)

    return _build_rebalancing_response(
        result=result,
        intent=intent,
        execution_id=execution_id,
        drift=drift,
        plan=plan,
        asset_lines=asset_lines,
        legacy_lock_abandoned=abandoned,
    )


def resume_rebalancing_portfolio(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    trigger: str = "manual",
) -> dict[str, Any]:
    """Reprise après signature LI.FI — quote leg suivant ou clôture terminal."""
    drift, plan = _compute_drift_and_plan(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    reconcile_running_v3_rebalance_execution(
        db,
        portfolio_id=str(portfolio_id),
        client_id=client_id,
        drift_rebalance_plan=plan,
        auto_progress=False,
        terminalize_plan_drift=False,
    )
    running = find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio_id))
    if running is None:
        terminal = find_latest_terminal_v3_rebalance_for_portfolio(
            db, portfolio_id=str(portfolio_id),
        )
        if terminal is not None:
            rebalance_exec_id = str(
                terminal.get("rebalance_execution_id")
                or terminal.get("batch_id")
                or "",
            )
            intent = (
                find_bundle_transaction_intent_by_rebalance_execution_id(
                    db,
                    rebalance_execution_id=rebalance_exec_id,
                )
                if rebalance_exec_id
                else None
            )
            asset_lines = _asset_lines_from_execution(terminal)
            execution_id = (
                UUID(rebalance_exec_id) if rebalance_exec_id else uuid.uuid4()
            )
            return _build_rebalancing_response(
                result=terminal,
                intent=intent,
                execution_id=execution_id,
                drift=drift,
                plan=plan,
                asset_lines=asset_lines,
                legacy_lock_abandoned=None,
            )
        raise RebalancingPortfolioError(
            "no_running_rebalance",
            "no_running_rebalance",
        )
    running_plan_hash = str(running.get("plan_hash") or "")
    current_plan_hash = str(plan.get("plan_hash") or "")
    plan_stale = bool(
        running_plan_hash
        and current_plan_hash
        and running_plan_hash != current_plan_hash
    )
    plan_replanned = False

    if plan_stale:
        force_terminalize_running_v3_rebalance_on_plan_drift(
            db,
            portfolio_id=str(portfolio_id),
            reason="plan_hash_changed",
        )
        plan_replanned = True

    try:
        if plan_replanned:
            result = execute_v3_bundle_rebalance(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                drift_rebalance_plan=plan,
                trigger=trigger,  # type: ignore[arg-type]
                plan_hash=current_plan_hash or None,
            )
        else:
            result = resume_v3_bundle_rebalance_execution(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                drift_rebalance_plan=plan,
                trigger=trigger,  # type: ignore[arg-type]
            )
    except BundleRebalanceExecutorError as exc:
        raise RebalancingPortfolioError("rebalancing_execution_failed", str(exc)) from exc

    v3_status = str(result.get("v3_status") or "")
    if v3_status in _TERMINAL_V3_STATUSES:
        release_active_bundle_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            failed=(v3_status == "FAILED"),
        )

    asset_lines = _asset_lines_from_execution(result)
    rebalance_exec_id = str(
        result.get("rebalance_execution_id") or running.get("rebalance_execution_id") or "",
    )
    intent = find_bundle_transaction_intent_by_rebalance_execution_id(
        db,
        rebalance_execution_id=rebalance_exec_id,
    )

    execution_id = UUID(rebalance_exec_id) if rebalance_exec_id else uuid.uuid4()
    if intent is not None:
        sync_bundle_transaction_rebalancing(intent, result=result, asset_lines=asset_lines)
        release_bundle_transaction_global_lock_on_v3_terminal(
            db,
            intent_id=intent.id,
            v3_status=v3_status,
        )
        db.add(intent)

    payload = _build_rebalancing_response(
        result=result,
        intent=intent,
        execution_id=execution_id,
        drift=drift,
        plan=plan,
        asset_lines=asset_lines,
        legacy_lock_abandoned=None,
    )
    if plan_replanned:
        payload["plan_replanned"] = True
        payload["plan_stale"] = True
    return payload


def _build_rebalancing_response(
    *,
    result: dict[str, Any],
    intent: TransactionIntent | None,
    execution_id: UUID,
    drift: dict[str, Any],
    plan: dict[str, Any],
    asset_lines: list[dict[str, str]],
    legacy_lock_abandoned: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "flow": REBALANCE_PORTFOLIO_FLOW_VERSION,
        "intent_id": str(intent.id) if intent is not None else None,
        "financial_operation_execution_id": str(execution_id),
        "drift_snapshot": drift,
        "rebalance_plan": plan,
        "asset_lines": asset_lines,
        **result,
    }
    if legacy_lock_abandoned is not None:
        payload["legacy_lock_abandoned"] = legacy_lock_abandoned
    return payload
