"""Bundle V3 Rebalancing Executor — exécute drift_rebalance_plan via LI.FI rail.

Le plan provient du planner PR-2. Pas de resume cross-batch ni resume_lifi_invest_batch.
"""
from __future__ import annotations

import logging
import os
import uuid as uuid_mod
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
ACTION_V3_TERMINAL = "v3_execution_terminal"

MAX_SWAP_ATTEMPTS = int(os.getenv("MAX_SWAP_ATTEMPTS", "2"))
QUOTE_TTL_SECONDS = int(os.getenv("QUOTE_TTL_SECONDS", "120"))

V3Trigger = Literal["manual", "deposit", "recovery", "cron"]

V3Status = Literal[
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_RESIDUAL_CASH",
    "FAILED",
    "NO_ACTION",
]


class BundleRebalanceExecutorError(Exception):
    """Erreur métier executor V3."""


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "instrument_id": self.instrument_id,
            "action": self.action,
            "amount_usdc": self.amount_usdc,
            "status": self.status,
            "attempts": self.attempts,
            "leg_ids": list(self.leg_ids),
            "swap_id": self.swap_id,
            "error": self.error,
        }


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
        """Exécute le plan V3. Idempotent si RUNNING existe déjà pour le même plan_hash."""
        resolved_hash = plan_hash or str(drift_rebalance_plan.get("plan_hash") or "")
        if not resolved_hash:
            raise BundleRebalanceExecutorError("plan_hash_required")

        existing = find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio_id))
        if existing is not None:
            if existing.get("plan_hash") == resolved_hash:
                return existing
            raise BundleRebalanceExecutorError(
                f"portfolio_has_running_rebalance:{portfolio_id}"
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
            )
            if not self._sells_allow_buy_phase(sell_results):
                self._expire_pending_legs(sell_results)
                terminal = self._build_terminal_response(
                    execution_id=execution_id,
                    batch_id=batch_id,
                    portfolio_id=str(portfolio_id),
                    plan_hash=resolved_hash,
                    trigger=trigger,
                    drift_rebalance_plan=drift_rebalance_plan,
                    sell_results=sell_results,
                    buy_results=[],
                    started_at=started_at,
                )
                self._audit_terminal(db, execution_id, terminal, actor)
                return terminal

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
            )

        self._expire_pending_legs(sell_results + buy_results)
        terminal = self._build_terminal_response(
            execution_id=execution_id,
            batch_id=batch_id,
            portfolio_id=str(portfolio_id),
            plan_hash=resolved_hash,
            trigger=trigger,
            drift_rebalance_plan=drift_rebalance_plan,
            sell_results=sell_results,
            buy_results=buy_results,
            started_at=started_at,
        )
        self._audit_terminal(db, execution_id, terminal, actor)
        return terminal

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
    ) -> list[V3LegExecutionResult]:
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

                leg = ExecutionLeg(
                    leg_id=leg_id,
                    portfolio_id=portfolio_id,
                    client_id=client_id,
                    action=leg_action,  # type: ignore[arg-type]
                    from_asset=from_asset,
                    to_asset=to_asset,
                    amount_from=amount_from,
                    batch_id=batch_id,
                    bundle_action="rebalance_v3",
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
                    exec_result = self._execution.execute_leg(db, leg, actor)
                except Exception as exc:
                    leg_result.status = "failed"
                    leg_result.error = str(exc)[:500]
                    if attempt >= MAX_SWAP_ATTEMPTS:
                        break
                    continue

                leg_result.swap_id = exec_result.provider_order_id
                leg_result.status = self._map_leg_status(exec_result)
                leg_result.error = ""

                if leg_result.status == "completed":
                    break
                if leg_result.status == "pending":
                    break
                if attempt >= MAX_SWAP_ATTEMPTS:
                    break

            results.append(leg_result)
        return results

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
            v3_status = self._resolve_terminal_status(sell_results, buy_results)

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
    ) -> V3Status:
        all_results = sell_results + buy_results
        if not all_results:
            return "NO_ACTION"

        completed = [r for r in all_results if r.status == "completed"]
        expired_or_failed = [
            r for r in all_results if r.status in ("failed", "expired")
        ]

        if completed and expired_or_failed:
            return "COMPLETED_WITH_RESIDUAL_CASH"
        if completed and not expired_or_failed:
            return "COMPLETED"
        if expired_or_failed and not completed:
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


def find_running_v3_rebalance_execution(
    db: Session,
    *,
    portfolio_id: str,
) -> dict[str, Any] | None:
    """Retourne l'exécution RUNNING la plus récente pour un portfolio, si pas encore terminalisée."""
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action.in_((ACTION_V3_RUNNING, ACTION_V3_TERMINAL)),
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    terminal_ids: set[str] = set()
    for row in rows:
        if row.action == ACTION_V3_TERMINAL and row.entity_id:
            terminal_ids.add(str(row.entity_id))

    for row in rows:
        if row.action != ACTION_V3_RUNNING:
            continue
        meta = row.metadata_ or {}
        if str(meta.get("portfolio_id")) != str(portfolio_id):
            continue
        exec_id = str(row.entity_id or "")
        if exec_id in terminal_ids:
            continue
        if meta.get("v3_status") == "RUNNING":
            return dict(meta)
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
