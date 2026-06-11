"""Bundle V3 Rebalancing Executor — exécute drift_rebalance_plan via LI.FI rail.

Le plan provient du planner PR-2. Pas de resume cross-batch ni resume_lifi_invest_batch.
"""
from __future__ import annotations

import logging
import os
import uuid as uuid_mod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Literal, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.service import ExchangeService
from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.lifi_base_config import normalize_bundle_asset
from services.portfolio_engine.bundle_execution.types import ExecutionLeg, ExecutionResult
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.security.context import ActorContext

from .orchestrator import BundleOrchestrator

logger = logging.getLogger(__name__)

ENTITY_TYPE_V3_REBALANCE = "bundle_rebalance_v3"
ACTION_V3_RUNNING = "v3_execution_running"
ACTION_V3_PROGRESS = "v3_execution_progress"
ACTION_V3_TERMINAL = "v3_execution_terminal"

MAX_SWAP_ATTEMPTS = int(os.getenv("MAX_SWAP_ATTEMPTS", "2"))
QUOTE_TTL_SECONDS = int(os.getenv("QUOTE_TTL_SECONDS", "120"))
MAX_EXECUTION_AGE_MINUTES = int(os.getenv("MAX_EXECUTION_AGE_MINUTES", "30"))


def client_signature_stale_minutes() -> int:
    raw = (os.environ.get("CLIENT_SIGNATURE_STALE_MINUTES") or "10").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 10

V3Trigger = Literal["manual", "deposit", "recovery", "cron"]
CLIENT_SIGNATURE_TRIGGERS: frozenset[V3Trigger] = frozenset({"manual"})
PAUSE_ON_PENDING_TRIGGERS: frozenset[V3Trigger] = frozenset({"manual", "deposit"})
WORKER_RESUME_TRIGGERS: frozenset[V3Trigger] = frozenset({"deposit"})


def _uses_client_signature(trigger: V3Trigger) -> bool:
    """Triggers où chaque leg LI.FI est signé côté client (confirm → sign → poll)."""
    return trigger in CLIENT_SIGNATURE_TRIGGERS


def _quote_all_legs_upfront(trigger: V3Trigger, leg_action: str) -> bool:
    """Rééquilibrage manuel = un swap unitaire par cycle HTTP (ADR 008).

    Chaque vente ou achat est un swap LI.FI indépendant (quote + signature Privy).
    Le leg suivant est quoté uniquement via POST /rebalancing/resume après clôture
    du swap courant — jamais de quotes ou signatures groupées.
    """
    _ = (trigger, leg_action)
    return False


def _pause_on_pending_leg(trigger: V3Trigger) -> bool:
    """Pause le cycle V3 tant qu'un leg LI.FI n'est pas terminal (manuel ou dépôt worker)."""
    return trigger in PAUSE_ON_PENDING_TRIGGERS


def _sync_legs_from_swaps_on_resume(trigger: V3Trigger) -> bool:
    return trigger in CLIENT_SIGNATURE_TRIGGERS or trigger in WORKER_RESUME_TRIGGERS


def _skip_plan_drift_terminalize(trigger: str) -> bool:
    """Après funding dépôt, le plan_hash drift est attendu — ne pas clôturer."""
    return trigger == "deposit"


def _plan_leg_assets(plan_legs: list[dict[str, Any]]) -> set[str]:
    return {
        str(leg.get("asset") or "").strip()
        for leg in plan_legs
        if str(leg.get("asset") or "").strip()
    }


def has_unquoted_plan_legs(
    *,
    sell_plan: list[dict[str, Any]],
    buy_plan: list[dict[str, Any]],
    sell_results: list["V3LegExecutionResult"],
    buy_results: list["V3LegExecutionResult"],
) -> bool:
    """True si le plan prévoit des actifs jamais quotés (absents des results)."""
    for plan, results in ((sell_plan, sell_results), (buy_plan, buy_results)):
        quoted = {r.asset for r in results}
        for asset in _plan_leg_assets(plan):
            if asset not in quoted:
                return True
    return False


def _execution_age_minutes(running: dict[str, Any]) -> float | None:
    started_raw = running.get("started_at")
    if not started_raw:
        return None
    try:
        started = datetime.fromisoformat(str(started_raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (
        datetime.now(timezone.utc) - started.astimezone(timezone.utc)
    ).total_seconds() / 60.0


def _within_client_rebalance_grace(running: dict[str, Any]) -> bool:
    age = _execution_age_minutes(running)
    if age is None:
        return False
    return age < float(client_signature_stale_minutes())

V3Status = Literal[
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_RESIDUAL_CASH",
    "FAILED",
    "NO_ACTION",
]


class BundleRebalanceExecutorError(Exception):
    """Erreur métier executor V3."""


def _leg_quote_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(Decimal(str(value)))
    except Exception:
        return None


def _apply_leg_quote_fields(
    leg_result: "V3LegExecutionResult",
    *,
    amount_in: str | Decimal | None = None,
    estimated_receive: str | Decimal | None = None,
    from_asset: str | None = None,
    to_asset: str | None = None,
) -> None:
    if amount_in is not None and str(amount_in) != "":
        leg_result.amount_in = _dec_str(Decimal(str(amount_in)))
    if estimated_receive is not None and str(estimated_receive) != "":
        leg_result.estimated_receive = _dec_str(Decimal(str(estimated_receive)))
    if from_asset:
        leg_result.from_asset = str(from_asset)
    if to_asset:
        leg_result.to_asset = str(to_asset)


@dataclass
class V3LegExecutionResult:
    asset: str
    instrument_id: str
    action: str
    amount_usdc: str
    status: str
    attempts: int
    leg_ids: list[str] = field(default_factory=list)
    swap_id: str | None = None
    error: str = ""
    attempt_details: list[dict[str, Any]] = field(default_factory=list)
    amount_in: str = ""
    estimated_receive: str = ""
    from_asset: str = ""
    to_asset: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "asset": self.asset,
            "instrument_id": self.instrument_id,
            "action": self.action,
            "amount_usdc": self.amount_usdc,
            "status": self.status,
            "attempts": self.attempts,
            "leg_ids": list(self.leg_ids),
            "swap_id": self.swap_id,
            "error": self.error,
            "attempt_details": list(self.attempt_details),
        }
        if self.amount_in:
            payload["amount_in"] = self.amount_in
        if self.estimated_receive:
            payload["estimated_receive"] = self.estimated_receive
        if self.from_asset:
            payload["from_asset"] = self.from_asset
        if self.to_asset:
            payload["to_asset"] = self.to_asset
        if self.action == "sell":
            qty = _leg_quote_float(self.amount_in)
            recv = _leg_quote_float(self.estimated_receive)
            if qty is not None:
                payload["quantity_sold"] = qty
            if recv is not None:
                payload["entry_asset_received"] = recv
        elif self.action == "buy":
            spent = _leg_quote_float(self.amount_in)
            qty = _leg_quote_float(self.estimated_receive)
            if spent is not None:
                payload["entry_asset_spent"] = spent
            if qty is not None:
                payload["quantity_bought"] = qty
        return payload


class BundleRebalanceExecutor:
    """Exécute un drift_rebalance_plan V3 — sell puis buy, terminal obligatoire."""

    def __init__(
        self,
        execution_adapter: Optional[BundleExecutionAdapter] = None,
        exchange_service: Optional[ExchangeService] = None,
    ):
        self._execution = execution_adapter or BundleExecutionAdapter()
        self._exchange = exchange_service or ExchangeService()

    def execute_drift_rebalance_plan(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        drift_rebalance_plan: dict[str, Any],
        trigger: V3Trigger = "manual",
        plan_hash: str | None = None,
    ) -> dict[str, Any]:
        """Exécute le plan V3. Idempotent par plan_hash — pas de swaps dupliqués."""
        resolved_hash = plan_hash or str(drift_rebalance_plan.get("plan_hash") or "")
        if not resolved_hash:
            raise BundleRebalanceExecutorError("plan_hash_required")

        stale = terminalize_stale_v3_rebalance_execution(
            db, portfolio_id=str(portfolio_id),
        )
        if stale is not None:
            logger.info(
                "v3_rebalance_stale_terminalized portfolio=%s execution=%s status=%s",
                portfolio_id,
                stale.get("rebalance_execution_id"),
                stale.get("v3_status"),
            )

        terminal_existing = find_terminal_v3_rebalance_by_plan_hash(
            db,
            portfolio_id=str(portfolio_id),
            plan_hash=resolved_hash,
        )
        if terminal_existing is not None:
            return terminal_existing

        existing = find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio_id))
        if existing is not None:
            existing_hash = str(existing.get("plan_hash") or "")
            if existing_hash == resolved_hash or _skip_plan_drift_terminalize(trigger):
                resume_plan = dict(drift_rebalance_plan)
                resume_hash = existing_hash or resolved_hash
                if _skip_plan_drift_terminalize(trigger) and existing_hash != resolved_hash:
                    resume_plan = {
                        **resume_plan,
                        "plan_hash": resume_hash,
                        "sell_plan": list(existing.get("sell_plan") or resume_plan.get("sell_plan") or []),
                        "buy_plan": list(existing.get("buy_plan") or resume_plan.get("buy_plan") or []),
                    }
                    logger.info(
                        "v3_rebalance_deposit_resume_frozen_plan portfolio=%s execution=%s "
                        "running_hash=%s fresh_hash=%s",
                        portfolio_id,
                        existing.get("rebalance_execution_id"),
                        existing_hash,
                        resolved_hash,
                    )
                return self._resume_running_execution(
                    db,
                    client_id=client_id,
                    portfolio_id=portfolio_id,
                    running=existing,
                    drift_rebalance_plan=resume_plan,
                    trigger=trigger,
                    plan_hash=resume_hash,
                )
            terminated = force_terminalize_running_v3_rebalance_on_plan_drift(
                db,
                portfolio_id=str(portfolio_id),
                reason="plan_hash_mismatch",
            )
            if terminated is not None:
                logger.info(
                    "v3_rebalance_plan_drift_terminalized portfolio=%s execution=%s "
                    "old_hash=%s new_hash=%s status=%s",
                    portfolio_id,
                    terminated.get("rebalance_execution_id"),
                    existing_hash,
                    resolved_hash,
                    terminated.get("v3_status"),
                )

        if drift_rebalance_plan.get("status") == "no_action":
            return self._no_action_response(
                portfolio_id=portfolio_id,
                plan_hash=resolved_hash,
                trigger=trigger,
            )

        sell_plan = list(drift_rebalance_plan.get("sell_plan") or [])
        buy_plan = list(drift_rebalance_plan.get("buy_plan") or [])
        if not sell_plan and not buy_plan:
            return self._no_action_response(
                portfolio_id=portfolio_id,
                plan_hash=resolved_hash,
                trigger=trigger,
            )

        portfolio = BundleOrchestrator._load_and_validate_portfolio(
            db, portfolio_id, client_id,
        )
        product = BundleOrchestrator._load_product(db, portfolio)
        entry_config = BundleOrchestrator._resolve_entry_config(product)
        entry_asset = str(
            drift_rebalance_plan.get("entry_asset")
            or entry_config["entry_asset_default"]
        ).upper()
        entry_instrument = BundleOrchestrator._resolve_or_create_instrument(db, entry_asset)

        execution_id = str(uuid_mod.uuid4())
        batch_id = execution_id
        actor = ActorContext(
            actor_type="system",
            actor_id=f"bundle-rebalance-v3-{portfolio_id}",
        )

        started_at = datetime.now(timezone.utc).isoformat()
        running_payload = {
            "rebalance_execution_id": execution_id,
            "batch_id": batch_id,
            "portfolio_id": str(portfolio_id),
            "client_id": str(client_id),
            "plan_hash": resolved_hash,
            "snapshot_hash": drift_rebalance_plan.get("snapshot_hash"),
            "trigger": trigger,
            "v3_status": "RUNNING",
            "weight_basis": drift_rebalance_plan.get("weight_basis"),
            "cash_funding_source": drift_rebalance_plan.get("cash_funding_source"),
            "available_cash_usdc": drift_rebalance_plan.get("available_cash_usdc"),
            "sell_plan": sell_plan,
            "buy_plan": buy_plan,
            "started_at": started_at,
            "sell_results": [],
            "buy_results": [],
        }
        self._audit_running(db, execution_id, running_payload, actor)
        db.flush()

        if _uses_client_signature(trigger):
            from services.portfolio_engine.wallets.resolver import ensure_portfolio_wallets

            spot_ids: list[UUID] = []
            for leg in sell_plan + buy_plan:
                raw_inst = leg.get("instrument_id")
                if raw_inst:
                    spot_ids.append(UUID(str(raw_inst)))
            ensure_portfolio_wallets(
                db,
                portfolio_id=portfolio_id,
                client_id=client_id,
                spot_instrument_ids=spot_ids,
                entry_instrument_id=entry_instrument.id,
            )

        sell_results: list[V3LegExecutionResult] = []
        buy_results: list[V3LegExecutionResult] = []

        if sell_plan:
            sell_results = self._execute_plan_legs(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                execution_id=execution_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                plan_legs=sell_plan,
                leg_action="rebalance_sell",
                actor=actor,
                trigger=trigger,
            )
            if not self._sells_allow_buy_phase(sell_results):
                return self._complete_execution_cycle(
                    db,
                    execution_id=execution_id,
                    batch_id=batch_id,
                    portfolio_id=str(portfolio_id),
                    plan_hash=resolved_hash,
                    trigger=trigger,
                    drift_rebalance_plan=drift_rebalance_plan,
                    sell_results=sell_results,
                    buy_results=[],
                    started_at=started_at,
                    running_payload=running_payload,
                    actor=actor,
                )
            running_resp = self._maybe_running_after_legs(
                db,
                execution_id=execution_id,
                batch_id=batch_id,
                portfolio_id=str(portfolio_id),
                plan_hash=resolved_hash,
                trigger=trigger,
                drift_rebalance_plan=drift_rebalance_plan,
                sell_results=sell_results,
                buy_results=buy_results,
                started_at=started_at,
                running_payload=running_payload,
                actor=actor,
            )
            if running_resp is not None:
                return running_resp

        if buy_plan:
            buy_results = self._execute_plan_legs(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                execution_id=execution_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                plan_legs=buy_plan,
                leg_action="rebalance_buy",
                actor=actor,
                trigger=trigger,
            )

        return self._complete_execution_cycle(
            db,
            execution_id=execution_id,
            batch_id=batch_id,
            portfolio_id=str(portfolio_id),
            plan_hash=resolved_hash,
            trigger=trigger,
            drift_rebalance_plan=drift_rebalance_plan,
            sell_results=sell_results,
            buy_results=buy_results,
            started_at=started_at,
            running_payload=running_payload,
            actor=actor,
        )

    def _resume_running_execution(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        running: dict[str, Any],
        drift_rebalance_plan: dict[str, Any],
        trigger: V3Trigger,
        plan_hash: str,
    ) -> dict[str, Any]:
        """Reprise après crash ou double-clic — même execution_id, legs déjà faits ignorés."""
        execution_id = str(running["rebalance_execution_id"])
        batch_id = str(running.get("batch_id") or execution_id)
        started_at = str(running.get("started_at") or datetime.now(timezone.utc).isoformat())
        actor = ActorContext(
            actor_type="system",
            actor_id=f"bundle-rebalance-v3-{portfolio_id}",
        )

        portfolio = BundleOrchestrator._load_and_validate_portfolio(
            db, portfolio_id, client_id,
        )
        product = BundleOrchestrator._load_product(db, portfolio)
        entry_config = BundleOrchestrator._resolve_entry_config(product)
        entry_asset = str(
            drift_rebalance_plan.get("entry_asset")
            or entry_config["entry_asset_default"]
        ).upper()
        entry_instrument = BundleOrchestrator._resolve_or_create_instrument(db, entry_asset)

        sell_results = _results_from_metadata(running.get("sell_results") or [])
        buy_results = _results_from_metadata(running.get("buy_results") or [])

        if _sync_legs_from_swaps_on_resume(trigger):
            sell_results = self._sync_leg_results_from_swaps(db, sell_results)
            buy_results = self._sync_leg_results_from_swaps(db, buy_results)

        sell_plan = list(drift_rebalance_plan.get("sell_plan") or [])
        buy_plan = list(drift_rebalance_plan.get("buy_plan") or [])
        running_payload = dict(running)

        if sell_plan:
            sell_results = self._execute_remaining_legs(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                execution_id=execution_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                plan_legs=sell_plan,
                leg_action="rebalance_sell",
                actor=actor,
                existing_results=sell_results,
                trigger=trigger,
            )
            if not self._sells_allow_buy_phase(sell_results):
                return self._complete_execution_cycle(
                    db,
                    execution_id=execution_id,
                    batch_id=batch_id,
                    portfolio_id=str(portfolio_id),
                    plan_hash=plan_hash,
                    trigger=trigger,
                    drift_rebalance_plan=drift_rebalance_plan,
                    sell_results=sell_results,
                    buy_results=buy_results,
                    started_at=started_at,
                    running_payload=running_payload,
                    actor=actor,
                )
            running_resp = self._maybe_running_after_legs(
                db,
                execution_id=execution_id,
                batch_id=batch_id,
                portfolio_id=str(portfolio_id),
                plan_hash=plan_hash,
                trigger=trigger,
                drift_rebalance_plan=drift_rebalance_plan,
                sell_results=sell_results,
                buy_results=buy_results,
                started_at=started_at,
                running_payload=running_payload,
                actor=actor,
            )
            if running_resp is not None:
                return running_resp

        if buy_plan:
            buy_results = self._execute_remaining_legs(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                execution_id=execution_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                plan_legs=buy_plan,
                leg_action="rebalance_buy",
                actor=actor,
                existing_results=buy_results,
                trigger=trigger,
            )

        return self._complete_execution_cycle(
            db,
            execution_id=execution_id,
            batch_id=batch_id,
            portfolio_id=str(portfolio_id),
            plan_hash=plan_hash,
            trigger=trigger,
            drift_rebalance_plan=drift_rebalance_plan,
            sell_results=sell_results,
            buy_results=buy_results,
            started_at=started_at,
            running_payload=running_payload,
            actor=actor,
        )

    def _execute_remaining_legs(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        batch_id: str,
        execution_id: str,
        entry_asset: str,
        entry_instrument_id: UUID,
        plan_legs: list[dict[str, Any]],
        leg_action: str,
        actor: ActorContext,
        existing_results: list[V3LegExecutionResult],
        trigger: V3Trigger,
    ) -> list[V3LegExecutionResult]:
        done_assets = {
            r.asset
            for r in existing_results
            if r.status == "completed"
            or (
                r.status == "pending"
                and r.error in ("awaiting_client_signature", "awaiting_confirmation")
            )
        }
        remaining_plan = [
            leg for leg in plan_legs if str(leg.get("asset") or "") not in done_assets
        ]
        if not remaining_plan:
            return existing_results
        new_results = self._execute_plan_legs(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            execution_id=execution_id,
            entry_asset=entry_asset,
            entry_instrument_id=entry_instrument_id,
            plan_legs=remaining_plan,
            leg_action=leg_action,
            actor=actor,
            trigger=trigger,
        )
        merged = {r.asset: r for r in existing_results}
        for row in new_results:
            merged[row.asset] = row
        return sorted(merged.values(), key=lambda r: r.asset)

    def _execute_plan_legs(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        batch_id: str,
        execution_id: str,
        entry_asset: str,
        entry_instrument_id: UUID,
        plan_legs: list[dict[str, Any]],
        leg_action: str,
        actor: ActorContext,
        trigger: V3Trigger,
    ) -> list[V3LegExecutionResult]:
        pause_on_pending = _pause_on_pending_leg(trigger)
        quote_all_legs_upfront = _quote_all_legs_upfront(trigger, leg_action)
        results: list[V3LegExecutionResult] = []
        sorted_legs = sorted(
            plan_legs,
            key=lambda r: Decimal(str(r.get("amount_usdc") or "0")),
            reverse=True,
        )
        for item in sorted_legs:
            asset = str(item.get("asset") or "")
            instrument_id = UUID(str(item["instrument_id"]))
            amount_usdc = Decimal(str(item.get("amount_usdc") or "0"))
            if amount_usdc <= 0:
                continue

            leg_result = V3LegExecutionResult(
                asset=asset,
                instrument_id=str(instrument_id),
                action="sell" if leg_action == "rebalance_sell" else "buy",
                amount_usdc=_dec_str(amount_usdc),
                status="pending",
                attempts=0,
            )

            if leg_action == "rebalance_sell":
                amount_from = self._usdc_to_crypto_quantity(
                    db, asset=asset, amount_usdc=amount_usdc, entry_asset=entry_asset,
                )
                from_asset = normalize_bundle_asset(asset)
                to_asset = entry_asset
                spot_instrument_id = instrument_id
            else:
                amount_from = amount_usdc
                from_asset = entry_asset
                to_asset = normalize_bundle_asset(asset)
                spot_instrument_id = instrument_id

            for attempt in range(1, MAX_SWAP_ATTEMPTS + 1):
                leg_id = (
                    f"v3-rebal-{execution_id[:8]}-{leg_action}-{asset}-a{attempt}"
                )
                leg_result.attempts = attempt
                leg_result.leg_ids.append(leg_id)

                from services.portfolio_engine.wallets.resolver import (
                    ensure_portfolio_wallets,
                    resolve_trade_wallets_for_leg,
                )
                from services.trade_core.execute_trade import execute_trade
                from services.trade_core.types import TradeRequest

                ensure_portfolio_wallets(
                    db,
                    portfolio_id=portfolio_id,
                    client_id=client_id,
                    spot_instrument_ids=[spot_instrument_id],
                    entry_instrument_id=entry_instrument_id,
                )
                if leg_action == "rebalance_sell":
                    wallet_from_id, wallet_to_id = resolve_trade_wallets_for_leg(
                        db,
                        portfolio_id=portfolio_id,
                        client_id=client_id,
                        leg_action=leg_action,
                        from_instrument_id=spot_instrument_id,
                        to_instrument_id=entry_instrument_id,
                        entry_instrument_id=entry_instrument_id,
                    )
                    instrument_from_id = spot_instrument_id
                    instrument_to_id = entry_instrument_id
                else:
                    wallet_from_id, wallet_to_id = resolve_trade_wallets_for_leg(
                        db,
                        portfolio_id=portfolio_id,
                        client_id=client_id,
                        leg_action=leg_action,
                        from_instrument_id=entry_instrument_id,
                        to_instrument_id=spot_instrument_id,
                        entry_instrument_id=entry_instrument_id,
                    )
                    instrument_from_id = entry_instrument_id
                    instrument_to_id = spot_instrument_id

                trade_req = TradeRequest(
                    wallet_from_id=wallet_from_id,
                    wallet_to_id=wallet_to_id,
                    instrument_from_id=instrument_from_id,
                    instrument_to_id=instrument_to_id,
                    quantity_from=amount_from,
                    correlation_id=UUID(execution_id),
                    client_id=client_id,
                    portfolio_id=portfolio_id,
                    from_asset=from_asset,
                    to_asset=to_asset,
                    leg_id=leg_id,
                    batch_id=batch_id,
                    bundle_action="rebalance_v3",
                    leg_action=leg_action,
                    chain="base",
                    metadata={
                        "entry_instrument_id": str(entry_instrument_id),
                        "target_instrument_id": str(spot_instrument_id),
                        "rebalance_execution_id": execution_id,
                        "planner_amount_usdc": _dec_str(amount_usdc),
                        "attempt": attempt,
                        "max_swap_attempts": MAX_SWAP_ATTEMPTS,
                    },
                )
                try:
                    trade_result = execute_trade(db, trade_req, actor)
                    exec_result = ExecutionResult(
                        leg_id=trade_result.leg_id,
                        status=(
                            "pending"
                            if trade_result.status in ("awaiting_signature", "pending")
                            else "completed"
                            if trade_result.status == "confirmed"
                            else "failed"
                        ),
                        from_asset=trade_result.from_asset,
                        to_asset=trade_result.to_asset,
                        amount_from=trade_result.amount_from,
                        amount_to=trade_result.amount_to,
                        tx_hash=trade_result.tx_hash,
                        provider_order_id=str(trade_result.swap_id),
                        raw=trade_result.raw,
                    )
                except Exception as exc:
                    leg_result.status = "failed"
                    leg_result.error = str(exc)[:500]
                    leg_result.attempt_details.append({
                        "attempt_index": attempt,
                        "leg_id": leg_id,
                        "status": "failed",
                        "error_code": "execution_exception",
                        "error": leg_result.error,
                    })
                    if attempt >= MAX_SWAP_ATTEMPTS:
                        break
                    continue

                leg_result.swap_id = exec_result.provider_order_id
                _apply_leg_quote_fields(
                    leg_result,
                    amount_in=trade_result.amount_from,
                    estimated_receive=trade_result.amount_to,
                    from_asset=trade_result.from_asset,
                    to_asset=trade_result.to_asset,
                )
                leg_result.status = self._map_leg_status(exec_result)
                leg_result.error = ""
                leg_result.attempt_details.append({
                    "attempt_index": attempt,
                    "leg_id": leg_id,
                    "swap_id": leg_result.swap_id,
                    "status": leg_result.status,
                    "error_code": None,
                })

                if leg_result.status == "completed":
                    break

                if leg_result.status == "pending":
                    if _uses_client_signature(trigger):
                        leg_result.error = "awaiting_client_signature"
                        if leg_result.attempt_details:
                            leg_result.attempt_details[-1]["error_code"] = None
                        break

                    resolved_status, resolved_error = self._resolve_pending_leg(
                        db,
                        leg_result=leg_result,
                        exec_result=exec_result,
                        trigger=trigger,
                    )
                    leg_result.status = resolved_status
                    leg_result.error = resolved_error
                    if leg_result.attempt_details:
                        leg_result.attempt_details[-1]["status"] = resolved_status
                        leg_result.attempt_details[-1]["error_code"] = resolved_error or None

                    if resolved_status == "completed":
                        break
                    if resolved_status in ("expired", "failed"):
                        if attempt >= MAX_SWAP_ATTEMPTS:
                            break
                        continue
                    if attempt >= MAX_SWAP_ATTEMPTS:
                        break
                    continue

                if attempt >= MAX_SWAP_ATTEMPTS:
                    break

            results.append(leg_result)
            if (
                pause_on_pending
                and leg_result.status == "pending"
                and not quote_all_legs_upfront
            ):
                break
        return results

    def _resolve_pending_leg(
        self,
        db: Session,
        *,
        leg_result: V3LegExecutionResult,
        exec_result: ExecutionResult,
        trigger: V3Trigger,
    ) -> tuple[str, str]:
        """Résout un leg pending (quote LI.FI) — retryable si quote non exécutée."""
        from uuid import UUID

        from services.lifi.enums import SwapSessionStatus
        from services.lifi.models import PersonWalletSwap
        from services.portfolio_engine.bundle_execution.pe_settlement import swap_confirmed

        raw = exec_result.raw if isinstance(exec_result.raw, dict) else {}
        swap_id = leg_result.swap_id or raw.get("swap_id")
        if swap_id:
            try:
                swap_uuid = UUID(str(swap_id))
            except (TypeError, ValueError):
                swap_uuid = None
            if swap_uuid is not None:
                swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_uuid).first()
                if swap is not None:
                    if swap_confirmed(swap):
                        return "completed", ""
                    if swap.status in (
                        SwapSessionStatus.EXPIRED.value,
                        SwapSessionStatus.FAILED.value,
                    ):
                        return "expired", str(swap.status).lower()
                    if _uses_client_signature(trigger):
                        if swap.status in (
                            SwapSessionStatus.QUOTE_RECEIVED.value,
                            SwapSessionStatus.AWAITING_SIGNATURE.value,
                            SwapSessionStatus.PENDING.value,
                        ):
                            return "pending", "awaiting_client_signature"
                        if swap.status == SwapSessionStatus.SUBMITTED.value:
                            return "pending", "awaiting_confirmation"
                    elif trigger in WORKER_RESUME_TRIGGERS:
                        if swap.status in (
                            SwapSessionStatus.QUOTE_RECEIVED.value,
                            SwapSessionStatus.AWAITING_SIGNATURE.value,
                            SwapSessionStatus.PENDING.value,
                        ):
                            return "pending", "awaiting_wallet_signature"
                        if swap.status == SwapSessionStatus.SUBMITTED.value:
                            return "pending", "awaiting_confirmation"
                    else:
                        if swap.status in (
                            SwapSessionStatus.QUOTE_RECEIVED.value,
                            SwapSessionStatus.AWAITING_SIGNATURE.value,
                            SwapSessionStatus.PENDING.value,
                        ):
                            return "expired", "quote_ttl_expired"
                        if swap.status == SwapSessionStatus.SUBMITTED.value:
                            return "pending", "awaiting_confirmation"

        if raw.get("requires_client_signature"):
            if _uses_client_signature(trigger):
                return "pending", "awaiting_client_signature"
            if trigger in WORKER_RESUME_TRIGGERS:
                return "pending", "awaiting_wallet_signature"
            return "expired", "quote_ttl_expired"

        return "expired", "quote_ttl_expired"

    def _sync_leg_results_from_swaps(
        self,
        db: Session,
        results: list[V3LegExecutionResult],
    ) -> list[V3LegExecutionResult]:
        """Met à jour le statut leg depuis le swap LI.FI (post-signature client)."""
        from services.lifi.enums import SwapSessionStatus
        from services.lifi.lifi_execute_service import LifiExecuteService
        from services.lifi.models import PersonWalletSwap
        from services.portfolio_engine.bundle_execution.pe_settlement import swap_confirmed
        from services.settlement.swap_router import settle_confirmed_swap

        lifi_execute = LifiExecuteService()
        for row in results:
            if not row.swap_id:
                continue
            try:
                swap_uuid = UUID(str(row.swap_id))
            except (TypeError, ValueError):
                continue
            swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_uuid).first()
            if swap is None:
                continue
            _apply_leg_quote_fields(
                row,
                amount_in=swap.amount_in,
                estimated_receive=swap.estimated_receive,
                from_asset=swap.from_asset,
                to_asset=swap.to_asset,
            )
            if swap.status == SwapSessionStatus.SUBMITTED.value:
                lifi_execute.refresh_lifi_status(db, swap)
                db.refresh(swap)
            if swap_confirmed(swap):
                settle_confirmed_swap(db, swap)
                db.refresh(swap)
                row.status = "completed"
                row.error = ""
            elif swap.status in (
                SwapSessionStatus.EXPIRED.value,
                SwapSessionStatus.FAILED.value,
            ):
                row.status = "expired"
                row.error = str(swap.status).lower()
            elif swap.status == SwapSessionStatus.SUBMITTED.value:
                row.status = "pending"
                row.error = "awaiting_confirmation"
            elif swap.status in (
                SwapSessionStatus.QUOTE_RECEIVED.value,
                SwapSessionStatus.AWAITING_SIGNATURE.value,
                SwapSessionStatus.PENDING.value,
            ):
                row.status = "pending"
                row.error = "awaiting_client_signature"
        return results

    def _maybe_running_after_legs(
        self,
        db: Session,
        *,
        execution_id: str,
        batch_id: str,
        portfolio_id: str,
        plan_hash: str,
        trigger: V3Trigger,
        drift_rebalance_plan: dict[str, Any],
        sell_results: list[V3LegExecutionResult],
        buy_results: list[V3LegExecutionResult],
        started_at: str,
        running_payload: dict[str, Any],
        actor: ActorContext,
    ) -> dict[str, Any] | None:
        if not _pause_on_pending_leg(trigger):
            return None
        if any(r.status == "pending" for r in sell_results + buy_results):
            return self._build_running_response(
                execution_id=execution_id,
                batch_id=batch_id,
                portfolio_id=portfolio_id,
                plan_hash=plan_hash,
                trigger=trigger,
                drift_rebalance_plan=drift_rebalance_plan,
                sell_results=sell_results,
                buy_results=buy_results,
                started_at=started_at,
                running_payload=running_payload,
                actor=actor,
                db=db,
            )
        return None

    def _complete_execution_cycle(
        self,
        db: Session,
        *,
        execution_id: str,
        batch_id: str,
        portfolio_id: str,
        plan_hash: str,
        trigger: V3Trigger,
        drift_rebalance_plan: dict[str, Any],
        sell_results: list[V3LegExecutionResult],
        buy_results: list[V3LegExecutionResult],
        started_at: str,
        running_payload: dict[str, Any],
        actor: ActorContext,
    ) -> dict[str, Any]:
        pause_on_pending = _pause_on_pending_leg(trigger)
        if _sync_legs_from_swaps_on_resume(trigger):
            sell_results = self._sync_leg_results_from_swaps(db, sell_results)
            buy_results = self._sync_leg_results_from_swaps(db, buy_results)

        self._update_running_progress(
            db, execution_id, running_payload, sell_results, buy_results, actor,
        )

        if pause_on_pending and any(
            r.status == "pending" for r in sell_results + buy_results
        ):
            return self._build_running_response(
                execution_id=execution_id,
                batch_id=batch_id,
                portfolio_id=portfolio_id,
                plan_hash=plan_hash,
                trigger=trigger,
                drift_rebalance_plan=drift_rebalance_plan,
                sell_results=sell_results,
                buy_results=buy_results,
                started_at=started_at,
                running_payload=running_payload,
                actor=actor,
                db=db,
            )

        if not pause_on_pending:
            self._expire_pending_legs(sell_results + buy_results)

        terminal = self._build_terminal_response(
            execution_id=execution_id,
            batch_id=batch_id,
            portfolio_id=portfolio_id,
            plan_hash=plan_hash,
            trigger=trigger,
            drift_rebalance_plan=drift_rebalance_plan,
            sell_results=sell_results,
            buy_results=buy_results,
            started_at=started_at,
        )
        self._audit_terminal(db, execution_id, terminal, actor)
        return terminal

    def _build_running_response(
        self,
        *,
        execution_id: str,
        batch_id: str,
        portfolio_id: str,
        plan_hash: str,
        trigger: V3Trigger,
        drift_rebalance_plan: dict[str, Any],
        sell_results: list[V3LegExecutionResult],
        buy_results: list[V3LegExecutionResult],
        started_at: str,
        running_payload: dict[str, Any],
        actor: ActorContext,
        db: Session,
    ) -> dict[str, Any]:
        payload = dict(running_payload)
        payload.update({
            "rebalance_execution_id": execution_id,
            "batch_id": batch_id,
            "portfolio_id": portfolio_id,
            "plan_hash": plan_hash,
            "trigger": trigger,
            "v3_status": "RUNNING",
            "sell_results": [r.to_dict() for r in sell_results],
            "buy_results": [r.to_dict() for r in buy_results],
            "started_at": started_at,
            "resume_required": True,
            "client_signature_required": trigger in CLIENT_SIGNATURE_TRIGGERS,
        })
        self._update_running_progress(
            db, execution_id, payload, sell_results, buy_results, actor,
        )
        return {
            "rebalance_execution_id": execution_id,
            "batch_id": batch_id,
            "portfolio_id": portfolio_id,
            "plan_hash": plan_hash,
            "snapshot_hash": drift_rebalance_plan.get("snapshot_hash"),
            "trigger": trigger,
            "v3_status": "RUNNING",
            "weight_basis": drift_rebalance_plan.get("weight_basis"),
            "cash_funding_source": drift_rebalance_plan.get("cash_funding_source"),
            "available_cash_usdc": drift_rebalance_plan.get("available_cash_usdc"),
            "sell_plan": drift_rebalance_plan.get("sell_plan") or [],
            "buy_plan": drift_rebalance_plan.get("buy_plan") or [],
            "sell_results": [r.to_dict() for r in sell_results],
            "buy_results": [r.to_dict() for r in buy_results],
            "started_at": started_at,
            "resume_required": True,
            "client_signature_required": trigger in CLIENT_SIGNATURE_TRIGGERS,
            "max_swap_attempts": MAX_SWAP_ATTEMPTS,
            "quote_ttl_seconds": QUOTE_TTL_SECONDS,
            "execution_provider": self._execution.provider_name,
        }

    def _sells_allow_buy_phase(self, sell_results: list[V3LegExecutionResult]) -> bool:
        if not sell_results:
            return True
        for row in sell_results:
            if row.status == "pending":
                return False
            if row.status == "failed":
                return False
        return True

    def _build_terminal_response(
        self,
        *,
        execution_id: str,
        batch_id: str,
        portfolio_id: str,
        plan_hash: str,
        trigger: V3Trigger,
        drift_rebalance_plan: dict[str, Any],
        sell_results: list[V3LegExecutionResult],
        buy_results: list[V3LegExecutionResult],
        started_at: str,
        forced_status: V3Status | None = None,
    ) -> dict[str, Any]:
        if forced_status:
            v3_status: V3Status = forced_status
        else:
            v3_status = self._resolve_terminal_status(
                sell_results,
                buy_results,
                cash_remaining_usdc=drift_rebalance_plan.get("available_cash_usdc"),
                sell_plan=list(drift_rebalance_plan.get("sell_plan") or []),
                buy_plan=list(drift_rebalance_plan.get("buy_plan") or []),
            )

        cash_remaining = drift_rebalance_plan.get("available_cash_usdc")
        return {
            "rebalance_execution_id": execution_id,
            "batch_id": batch_id,
            "portfolio_id": portfolio_id,
            "plan_hash": plan_hash,
            "snapshot_hash": drift_rebalance_plan.get("snapshot_hash"),
            "trigger": trigger,
            "v3_status": v3_status,
            "weight_basis": drift_rebalance_plan.get("weight_basis"),
            "cash_funding_source": drift_rebalance_plan.get("cash_funding_source"),
            "available_cash_usdc": cash_remaining,
            "cash_remaining_usdc": cash_remaining if v3_status != "COMPLETED" else "0",
            "sell_plan": drift_rebalance_plan.get("sell_plan") or [],
            "buy_plan": drift_rebalance_plan.get("buy_plan") or [],
            "sell_results": [r.to_dict() for r in sell_results],
            "buy_results": [r.to_dict() for r in buy_results],
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "max_swap_attempts": MAX_SWAP_ATTEMPTS,
            "quote_ttl_seconds": QUOTE_TTL_SECONDS,
            "max_execution_age_minutes": MAX_EXECUTION_AGE_MINUTES,
            "execution_provider": self._execution.provider_name,
            "resume_required": False,
        }

    @staticmethod
    def _expire_pending_legs(results: list[V3LegExecutionResult]) -> None:
        """Pending → expired : pas de resume_required cross-batch (V3)."""
        for row in results:
            if row.status == "pending":
                row.status = "expired"
                row.error = row.error or "quote_ttl_expired"

    @staticmethod
    def _resolve_terminal_status(
        sell_results: list[V3LegExecutionResult],
        buy_results: list[V3LegExecutionResult],
        *,
        cash_remaining_usdc: str | Decimal | None = None,
        sell_plan: list[dict[str, Any]] | None = None,
        buy_plan: list[dict[str, Any]] | None = None,
    ) -> V3Status:
        all_results = sell_results + buy_results
        if not all_results:
            return "NO_ACTION"

        completed = [r for r in all_results if r.status == "completed"]
        expired_or_failed = [
            r for r in all_results if r.status in ("failed", "expired")
        ]
        unquoted_plan = has_unquoted_plan_legs(
            sell_plan=sell_plan or [],
            buy_plan=buy_plan or [],
            sell_results=sell_results,
            buy_results=buy_results,
        )

        if completed and expired_or_failed:
            return "COMPLETED_WITH_RESIDUAL_CASH"
        if completed and not expired_or_failed:
            if unquoted_plan:
                return "COMPLETED_WITH_RESIDUAL_CASH"
            return "COMPLETED"
        if expired_or_failed and not completed:
            cash = Decimal(str(cash_remaining_usdc or "0"))
            sell_blocked = any(
                r.status in ("failed", "expired", "pending") for r in sell_results
            )
            if sell_blocked:
                return "FAILED"
            if cash > 0:
                return "COMPLETED_WITH_RESIDUAL_CASH"
            return "FAILED"
        return "FAILED"

    @staticmethod
    def _map_leg_status(result: ExecutionResult) -> str:
        st = (result.status or "failed").lower()
        if st == "completed":
            return "completed"
        if st == "pending":
            return "pending"
        return "failed"

    def _usdc_to_crypto_quantity(
        self,
        db: Session,
        *,
        asset: str,
        amount_usdc: Decimal,
        entry_asset: str,
    ) -> Decimal:
        if amount_usdc <= 0:
            return Decimal("0")
        price_eur = self._exchange._resolve_price(db, asset, override_price=None, side="sell")
        entry_price_eur = self._exchange._resolve_price(
            db, entry_asset, override_price=None, side="sell",
        )
        if price_eur <= 0 or entry_price_eur <= 0:
            raise BundleRebalanceExecutorError(f"price_unavailable:{asset}")
        value_eur = amount_usdc * entry_price_eur
        qty = (value_eur / price_eur).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        return max(qty, Decimal("0"))

    @staticmethod
    def _no_action_response(
        *,
        portfolio_id: UUID,
        plan_hash: str,
        trigger: V3Trigger,
    ) -> dict[str, Any]:
        return {
            "rebalance_execution_id": None,
            "batch_id": None,
            "portfolio_id": str(portfolio_id),
            "plan_hash": plan_hash,
            "trigger": trigger,
            "v3_status": "NO_ACTION",
            "sell_results": [],
            "buy_results": [],
            "resume_required": False,
        }

    @staticmethod
    def _audit_running(
        db: Session,
        execution_id: str,
        payload: dict[str, Any],
        actor: ActorContext,
    ) -> None:
        AuditService.log_event(
            db,
            entity_type=ENTITY_TYPE_V3_REBALANCE,
            entity_id=execution_id,
            action=ACTION_V3_RUNNING,
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata=payload,
        )

    @staticmethod
    def _update_running_progress(
        db: Session,
        execution_id: str,
        running_payload: dict[str, Any],
        sell_results: list[V3LegExecutionResult],
        buy_results: list[V3LegExecutionResult],
        actor: ActorContext,
    ) -> None:
        payload = dict(running_payload)
        payload["sell_results"] = [r.to_dict() for r in sell_results]
        payload["buy_results"] = [r.to_dict() for r in buy_results]
        AuditService.log_event(
            db,
            entity_type=ENTITY_TYPE_V3_REBALANCE,
            entity_id=execution_id,
            action=ACTION_V3_PROGRESS,
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata=payload,
        )
        db.flush()

    @staticmethod
    def _audit_terminal(
        db: Session,
        execution_id: str,
        payload: dict[str, Any],
        actor: ActorContext,
    ) -> None:
        AuditService.log_event(
            db,
            entity_type=ENTITY_TYPE_V3_REBALANCE,
            entity_id=execution_id,
            action=ACTION_V3_TERMINAL,
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata=payload,
        )


def _dec_str(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN), "f")


def _latest_v3_metadata_by_execution(
    db: Session,
    *,
    portfolio_id: str,
) -> dict[str, dict[str, Any]]:
    """Dernier snapshot par execution_id (running / progress / terminal)."""
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action.in_(
                (ACTION_V3_RUNNING, ACTION_V3_PROGRESS, ACTION_V3_TERMINAL),
            ),
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(500)
        .all()
    )
    by_exec: dict[str, dict[str, Any]] = {}
    for row in rows:
        meta = row.metadata_ or {}
        if str(meta.get("portfolio_id")) != str(portfolio_id):
            continue
        exec_id = str(row.entity_id or "")
        if not exec_id or exec_id in by_exec:
            continue
        snapshot = dict(meta)
        snapshot["_audit_action"] = row.action
        by_exec[exec_id] = snapshot
    return by_exec


def _terminal_execution_ids_for_portfolio(
    db: Session,
    *,
    portfolio_id: str,
) -> set[str]:
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action == ACTION_V3_TERMINAL,
        )
        .all()
    )
    terminal_ids: set[str] = set()
    for row in rows:
        meta = row.metadata_ or {}
        if str(meta.get("portfolio_id")) != str(portfolio_id):
            continue
        exec_id = str(row.entity_id or meta.get("rebalance_execution_id") or "")
        if exec_id:
            terminal_ids.add(exec_id)
    return terminal_ids


def find_running_v3_rebalance_execution(
    db: Session,
    *,
    portfolio_id: str,
) -> dict[str, Any] | None:
    """Retourne l'exécution RUNNING la plus récente (snapshot progress le plus frais)."""
    terminal_ids = _terminal_execution_ids_for_portfolio(db, portfolio_id=portfolio_id)
    by_exec = _latest_v3_metadata_by_execution(db, portfolio_id=portfolio_id)
    running_candidates: list[dict[str, Any]] = []
    for snapshot in by_exec.values():
        exec_id = str(snapshot.get("rebalance_execution_id") or "")
        if exec_id in terminal_ids:
            continue
        if snapshot.get("_audit_action") == ACTION_V3_TERMINAL:
            continue
        if snapshot.get("v3_status") == "RUNNING":
            running_candidates.append(snapshot)
    if not running_candidates:
        return None
    running_candidates.sort(
        key=lambda s: str(s.get("started_at") or ""),
        reverse=True,
    )
    latest = running_candidates[0]
    latest.pop("_audit_action", None)
    return latest


def find_latest_terminal_v3_rebalance_for_portfolio(
    db: Session,
    *,
    portfolio_id: str,
    max_age_minutes: int = 60,
) -> dict[str, Any] | None:
    """Dernier cycle V3 terminal récent — reprise UI quand RUNNING déjà clôturé."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, max_age_minutes))
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action == ACTION_V3_TERMINAL,
            AuditEvent.created_at >= cutoff,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(80)
        .all()
    )
    pid = str(portfolio_id)
    for row in rows:
        meta = row.metadata_ or {}
        if str(meta.get("portfolio_id") or "") == pid:
            return dict(meta)
    return None


def find_terminal_v3_rebalance_by_plan_hash(
    db: Session,
    *,
    portfolio_id: str,
    plan_hash: str,
) -> dict[str, Any] | None:
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action == ACTION_V3_TERMINAL,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    for row in rows:
        meta = row.metadata_ or {}
        if (
            str(meta.get("portfolio_id")) == str(portfolio_id)
            and str(meta.get("plan_hash")) == str(plan_hash)
        ):
            return dict(meta)
    return None


def _force_terminalize_running_snapshot(
    db: Session,
    *,
    running: dict[str, Any],
    actor_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Clôture forcée d’un cycle RUNNING — expire les legs pending."""
    execution_id = str(running["rebalance_execution_id"])
    sell_results = _results_from_metadata(running.get("sell_results") or [])
    buy_results = _results_from_metadata(running.get("buy_results") or [])
    BundleRebalanceExecutor._expire_pending_legs(sell_results + buy_results)

    v3_status = BundleRebalanceExecutor._resolve_terminal_status(
        sell_results,
        buy_results,
        cash_remaining_usdc=running.get("available_cash_usdc"),
        sell_plan=list(running.get("sell_plan") or []),
        buy_plan=list(running.get("buy_plan") or []),
    )
    if v3_status == "RUNNING":
        v3_status = "COMPLETED_WITH_RESIDUAL_CASH"

    terminal = {
        **running,
        "v3_status": v3_status,
        "sell_results": [r.to_dict() for r in sell_results],
        "buy_results": [r.to_dict() for r in buy_results],
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "resume_required": False,
        **(extra or {}),
    }
    actor = ActorContext(actor_type="system", actor_id=actor_id)
    BundleRebalanceExecutor._audit_terminal(db, execution_id, terminal, actor)
    db.flush()
    return terminal


def terminalize_stale_v3_rebalance_execution(
    db: Session,
    *,
    portfolio_id: str,
) -> dict[str, Any] | None:
    """Force un cycle terminal si RUNNING > MAX_EXECUTION_AGE_MINUTES."""
    running = find_running_v3_rebalance_execution(db, portfolio_id=portfolio_id)
    if running is None:
        return None

    started_raw = running.get("started_at")
    if not started_raw:
        return None
    try:
        started = datetime.fromisoformat(str(started_raw).replace("Z", "+00:00"))
    except ValueError:
        return None

    age_minutes = (
        datetime.now(timezone.utc) - started.astimezone(timezone.utc)
    ).total_seconds() / 60.0
    if age_minutes < MAX_EXECUTION_AGE_MINUTES:
        return None

    return _force_terminalize_running_snapshot(
        db,
        running=running,
        actor_id="bundle-rebalance-v3-stale",
        extra={
            "stale_terminalized": True,
            "stale_age_minutes": round(age_minutes, 2),
            "max_execution_age_minutes": MAX_EXECUTION_AGE_MINUTES,
        },
    )


def force_terminalize_running_v3_rebalance_on_plan_drift(
    db: Session,
    *,
    portfolio_id: str,
    reason: str = "plan_hash_changed",
) -> dict[str, Any] | None:
    """Clôture RUNNING dont le plan_hash ne correspond plus au drift courant."""
    running = find_running_v3_rebalance_execution(db, portfolio_id=portfolio_id)
    if running is None:
        return None
    return _force_terminalize_running_snapshot(
        db,
        running=running,
        actor_id="bundle-rebalance-v3-plan-drift",
        extra={
            "plan_drift_terminalized": True,
            "plan_drift_reason": reason,
        },
    )


def _results_from_metadata(rows: list[dict[str, Any]]) -> list[V3LegExecutionResult]:
    out: list[V3LegExecutionResult] = []
    for row in rows:
        out.append(
            V3LegExecutionResult(
                asset=str(row.get("asset") or ""),
                instrument_id=str(row.get("instrument_id") or ""),
                action=str(row.get("action") or ""),
                amount_usdc=str(row.get("amount_usdc") or "0"),
                status=str(row.get("status") or "failed"),
                attempts=int(row.get("attempts") or 0),
                leg_ids=list(row.get("leg_ids") or []),
                swap_id=row.get("swap_id"),
                error=str(row.get("error") or ""),
                amount_in=str(row.get("amount_in") or ""),
                estimated_receive=str(row.get("estimated_receive") or ""),
                from_asset=str(row.get("from_asset") or ""),
                to_asset=str(row.get("to_asset") or ""),
            )
        )
    return out


def _release_v3_rebalance_guard(
    db: Session,
    *,
    portfolio_id: str,
    terminal: dict[str, Any],
) -> None:
    from services.portfolio_engine.financial_operations.wiring import (
        release_active_bundle_portfolio_operation,
    )

    try:
        pid = UUID(str(portfolio_id))
    except (TypeError, ValueError):
        return
    release_active_bundle_portfolio_operation(
        db,
        portfolio_id=pid,
        failed=str(terminal.get("v3_status") or "") == "FAILED",
    )
    from services.portfolio_engine.bundles.bundle_transaction_intent import (
        finalize_bundle_transaction_after_v3_terminal,
    )

    finalize_bundle_transaction_after_v3_terminal(
        db,
        portfolio_id=str(portfolio_id),
        terminal=terminal,
    )


def _expire_stale_client_signature_pending_legs(
    db: Session,
    results: list[V3LegExecutionResult],
    *,
    max_age_minutes: int | None = None,
) -> bool:
    """Pending awaiting_client_signature → expired si swap AWAITING_SIGNATURE trop vieux."""
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.lifi.swap_repository import PersonWalletSwapRepository

    ttl = client_signature_stale_minutes() if max_age_minutes is None else max(0, max_age_minutes)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ttl) if ttl > 0 else None
    repo = PersonWalletSwapRepository()
    changed = False

    for row in results:
        if row.status != "pending":
            continue
        if row.error not in (
            "awaiting_client_signature",
            "awaiting_wallet_signature",
            "awaiting_confirmation",
        ):
            continue
        if not row.swap_id:
            continue
        try:
            swap_uuid = UUID(str(row.swap_id))
        except (TypeError, ValueError):
            continue
        swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_uuid).first()
        if swap is None:
            row.status = "expired"
            row.error = "swap_missing"
            changed = True
            continue
        if swap.status not in (
            SwapSessionStatus.AWAITING_SIGNATURE.value,
            SwapSessionStatus.QUOTE_RECEIVED.value,
            SwapSessionStatus.PENDING.value,
        ):
            continue
        ref = swap.updated_at or swap.created_at
        if cutoff is not None and ref is not None and ref > cutoff:
            continue
        swap.status = SwapSessionStatus.EXPIRED.value
        swap.error_message = "Signature expirée — reprise impossible."
        repo.append_audit(
            swap,
            {
                "event": "client_signature_stale_expired",
                "max_age_minutes": ttl,
                "leg_asset": row.asset,
            },
        )
        db.add(swap)
        row.status = "expired"
        row.error = "client_signature_stale"
        changed = True

    if changed:
        db.flush()
    return changed


def _expire_unrecoverable_pending_legs(
    db: Session,
    results: list[V3LegExecutionResult],
) -> bool:
    """Pending → expired si le swap est terminal ou introuvable."""
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.portfolio_engine.bundle_execution.pe_settlement import swap_confirmed

    changed = False
    for row in results:
        if row.status != "pending":
            continue
        if not row.swap_id:
            row.status = "expired"
            row.error = row.error or "quote_ttl_expired"
            changed = True
            continue
        try:
            swap_uuid = UUID(str(row.swap_id))
        except (TypeError, ValueError):
            row.status = "expired"
            row.error = "swap_id_invalid"
            changed = True
            continue
        swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_uuid).first()
        if swap is None:
            row.status = "expired"
            row.error = "swap_missing"
            changed = True
            continue
        if swap_confirmed(swap):
            row.status = "completed"
            row.error = ""
            changed = True
        elif swap.status in (
            SwapSessionStatus.EXPIRED.value,
            SwapSessionStatus.FAILED.value,
        ):
            row.status = "expired"
            row.error = str(swap.status).lower()
            changed = True
    return changed


def _has_signable_pending_legs(results: list[V3LegExecutionResult]) -> bool:
    return any(
        r.status == "pending"
        and r.error in ("awaiting_client_signature", "awaiting_confirmation")
        for r in results
    )


def reconcile_running_v3_rebalance_execution(
    db: Session,
    *,
    portfolio_id: str,
    client_id: UUID | None = None,
    drift_rebalance_plan: dict[str, Any] | None = None,
    auto_progress: bool = True,
    terminalize_plan_drift: bool = True,
) -> dict[str, Any] | None:
    """Réconciliation read-path : sync swaps, expire legs mortes, terminalise ou progresse."""
    running = find_running_v3_rebalance_execution(db, portfolio_id=portfolio_id)
    if running is None:
        return None

    stale = terminalize_stale_v3_rebalance_execution(db, portfolio_id=portfolio_id)
    if stale is not None:
        _release_v3_rebalance_guard(db, portfolio_id=portfolio_id, terminal=stale)
        return stale

    trigger = str(running.get("trigger") or "manual")

    if terminalize_plan_drift and drift_rebalance_plan and not _skip_plan_drift_terminalize(trigger):
        current_hash = str(drift_rebalance_plan.get("plan_hash") or "")
        running_hash = str(running.get("plan_hash") or "")
        if current_hash and running_hash and current_hash != running_hash:
            terminal = force_terminalize_running_v3_rebalance_on_plan_drift(
                db,
                portfolio_id=portfolio_id,
                reason="plan_hash_changed_on_reconcile",
            )
            if terminal is not None:
                _release_v3_rebalance_guard(db, portfolio_id=portfolio_id, terminal=terminal)
            return terminal

    executor = BundleRebalanceExecutor()
    sell_results = _results_from_metadata(running.get("sell_results") or [])
    buy_results = _results_from_metadata(running.get("buy_results") or [])

    if _sync_legs_from_swaps_on_resume(trigger):  # type: ignore[arg-type]
        sell_results = executor._sync_leg_results_from_swaps(db, sell_results)
        buy_results = executor._sync_leg_results_from_swaps(db, buy_results)

    _expire_stale_client_signature_pending_legs(db, sell_results + buy_results)
    _expire_unrecoverable_pending_legs(db, sell_results + buy_results)

    all_results = sell_results + buy_results
    has_pending = any(r.status == "pending" for r in all_results)
    signable_pending = (
        trigger == "manual" and _has_signable_pending_legs(all_results)
    )

    execution_id = str(running["rebalance_execution_id"])
    actor = ActorContext(actor_type="system", actor_id="bundle-rebalance-v3-reconcile")
    running_payload = {
        **running,
        "sell_results": [r.to_dict() for r in sell_results],
        "buy_results": [r.to_dict() for r in buy_results],
    }

    if not has_pending:
        sell_plan = list(running.get("sell_plan") or [])
        buy_plan = list(running.get("buy_plan") or [])
        if (
            trigger == "manual"
            and drift_rebalance_plan is not None
            and has_unquoted_plan_legs(
                sell_plan=sell_plan,
                buy_plan=buy_plan,
                sell_results=sell_results,
                buy_results=buy_results,
            )
            and _within_client_rebalance_grace(running)
        ):
            return executor._build_running_response(
                db=db,
                execution_id=execution_id,
                batch_id=str(running.get("batch_id") or execution_id),
                portfolio_id=portfolio_id,
                plan_hash=str(running.get("plan_hash") or ""),
                trigger=trigger,  # type: ignore[arg-type]
                drift_rebalance_plan=drift_rebalance_plan,
                sell_results=sell_results,
                buy_results=buy_results,
                started_at=str(running.get("started_at") or ""),
                running_payload=running_payload,
                actor=actor,
            )

        terminal = _force_terminalize_running_snapshot(
            db,
            running=running_payload,
            actor_id="bundle-rebalance-v3-reconcile",
            extra={"reconciled_terminalized": True},
        )
        _release_v3_rebalance_guard(db, portfolio_id=portfolio_id, terminal=terminal)
        return terminal

    if (
        auto_progress
        and not signable_pending
        and client_id is not None
        and drift_rebalance_plan is not None
    ):
        try:
            result = executor._resume_running_execution(
                db,
                client_id=client_id,
                portfolio_id=UUID(str(portfolio_id)),
                running=running_payload,
                drift_rebalance_plan=drift_rebalance_plan,
                trigger=trigger,  # type: ignore[arg-type]
                plan_hash=str(running.get("plan_hash") or ""),
            )
            v3_status = str(result.get("v3_status") or "")
            if v3_status in ("COMPLETED", "COMPLETED_WITH_RESIDUAL_CASH", "FAILED", "NO_ACTION"):
                _release_v3_rebalance_guard(db, portfolio_id=portfolio_id, terminal=result)
            return result
        except Exception:
            logger.exception(
                "v3_rebalance_reconcile_auto_progress_failed portfolio=%s execution=%s",
                portfolio_id,
                execution_id,
            )

    BundleRebalanceExecutor._update_running_progress(
        db,
        execution_id,
        running_payload,
        sell_results,
        buy_results,
        actor,
    )
    db.flush()
    return None


def force_close_stale_signable_v3_rebalance(
    db: Session,
    *,
    portfolio_id: str,
    client_id: UUID | None = None,
    drift_rebalance_plan: dict[str, Any] | None = None,
    reason: str = "signable_force_close",
    max_age_minutes: int = 0,
) -> dict[str, Any] | None:
    """Expire les legs signature stale (ou immédiat si max_age=0) puis terminalise V3."""
    running = find_running_v3_rebalance_execution(db, portfolio_id=portfolio_id)
    if running is None:
        return None

    sell_results = _results_from_metadata(running.get("sell_results") or [])
    buy_results = _results_from_metadata(running.get("buy_results") or [])
    _expire_stale_client_signature_pending_legs(
        db,
        sell_results + buy_results,
        max_age_minutes=max_age_minutes,
    )
    _expire_unrecoverable_pending_legs(db, sell_results + buy_results)

    running_payload = {
        **running,
        "sell_results": [r.to_dict() for r in sell_results],
        "buy_results": [r.to_dict() for r in buy_results],
    }
    has_pending = any(
        r.status == "pending" for r in sell_results + buy_results
    )
    if not has_pending:
        terminal = _force_terminalize_running_snapshot(
            db,
            running=running_payload,
            actor_id="bundle-rebalance-v3-signable-force-close",
            extra={"signable_force_closed": True, "reason": reason},
        )
        _release_v3_rebalance_guard(db, portfolio_id=portfolio_id, terminal=terminal)
        return terminal

    if client_id is not None and drift_rebalance_plan is not None:
        terminal = reconcile_running_v3_rebalance_execution(
            db,
            portfolio_id=portfolio_id,
            client_id=client_id,
            drift_rebalance_plan=drift_rebalance_plan,
            auto_progress=False,
        )
        if terminal is not None:
            return terminal

    if max_age_minutes == 0:
        terminal = _force_terminalize_running_snapshot(
            db,
            running=running_payload,
            actor_id="bundle-rebalance-v3-signable-force-close",
            extra={
                "signable_force_closed": True,
                "reason": reason,
                "forced_with_pending": True,
            },
        )
        _release_v3_rebalance_guard(db, portfolio_id=portfolio_id, terminal=terminal)
        return terminal

    return None


def find_v3_execution_by_plan_hash(
    db: Session,
    *,
    portfolio_id: str,
    plan_hash: str,
) -> dict[str, Any] | None:
    """Dernière exécution (RUNNING ou terminal) pour portfolio + plan_hash."""
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action == ACTION_V3_TERMINAL,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    for row in rows:
        meta = row.metadata_ or {}
        if (
            str(meta.get("portfolio_id")) == str(portfolio_id)
            and str(meta.get("plan_hash")) == str(plan_hash)
        ):
            return dict(meta)

    running = find_running_v3_rebalance_execution(db, portfolio_id=portfolio_id)
    if running and running.get("plan_hash") == plan_hash:
        return running
    return None


def execute_v3_bundle_rebalance(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    drift_rebalance_plan: dict[str, Any],
    trigger: V3Trigger = "manual",
    plan_hash: str | None = None,
    execution_adapter: Optional[BundleExecutionAdapter] = None,
) -> dict[str, Any]:
    """Point d'entrée module — instancie l'executor et exécute le plan."""
    executor = BundleRebalanceExecutor(execution_adapter=execution_adapter)
    return executor.execute_drift_rebalance_plan(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        drift_rebalance_plan=drift_rebalance_plan,
        trigger=trigger,
        plan_hash=plan_hash,
    )


def resume_v3_bundle_rebalance_execution(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    drift_rebalance_plan: dict[str, Any],
    trigger: V3Trigger = "manual",
    execution_adapter: Optional[BundleExecutionAdapter] = None,
) -> dict[str, Any]:
    """Reprise après signature client — sync swaps, quote leg suivant ou terminal."""
    executor = BundleRebalanceExecutor(execution_adapter=execution_adapter)
    running = find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio_id))
    if running is None:
        raise BundleRebalanceExecutorError("no_running_rebalance")
    plan_hash = str(
        running.get("plan_hash") or drift_rebalance_plan.get("plan_hash") or "",
    )
    return executor._resume_running_execution(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        running=running,
        drift_rebalance_plan=drift_rebalance_plan,
        trigger=trigger,
        plan_hash=plan_hash,
    )
