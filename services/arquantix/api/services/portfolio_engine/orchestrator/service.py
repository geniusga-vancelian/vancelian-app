"""Rebalance Orchestrator (Phase 8 v1).

Connects strategy evaluation to rebalance preview creation.
Does NOT generate execution instructions, orders, or trades.

Orchestration modes:
- manual:    evaluate + log only
- assisted:  evaluate + create preview + log
- automatic: evaluate + create preview + log + mark execution_eligible
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..drift.service import DriftRebalanceService
from ..portfolios.models import Portfolio
from ..rebalancing.models import RebalancePolicy
from ..strategy_engine.enums import StrategyActionType
from ..strategy_engine.service import StrategyEngineService
from ..valuations.service import ValuationService
from .enums import OrchestrationStatus, RebalanceExecutionMode
from .repository import OrchestrationRunRepository
from .schemas import OrchestrationResult

ZERO = Decimal("0")


class PortfolioNotFoundForOrchestrationError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class OrchestrationRunNotFoundError(Exception):
    def __init__(self, run_id: UUID):
        self.run_id = run_id
        super().__init__(f"OrchestrationRun {run_id} not found")


class RebalanceOrchestratorService:

    def __init__(self) -> None:
        self._strategy_service = StrategyEngineService()
        self._drift_service = DriftRebalanceService()
        self._valuation_service = ValuationService()
        self._run_repo = OrchestrationRunRepository()

    def run_portfolio_cycle(
        self, db: Session, portfolio_id: UUID
    ) -> OrchestrationResult:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise PortfolioNotFoundForOrchestrationError(portfolio_id)

        now = datetime.now(timezone.utc)
        warnings: list[str] = []

        mode = self._resolve_mode(db, portfolio_id)

        run = self._run_repo.create(db, data={
            "portfolio_id": portfolio_id,
            "mode": mode,
            "status": OrchestrationStatus.STARTED,
            "started_at": now,
            "metadata_": {},
        })

        try:
            return self._execute_cycle(db, run, portfolio_id, mode, now, warnings)
        except Exception as exc:
            self._run_repo.update(db, run, data={
                "status": OrchestrationStatus.FAILED,
                "abort_reason": str(exc)[:500],
                "completed_at": datetime.now(timezone.utc),
            })
            raise

    # ------------------------------------------------------------------
    # Core cycle
    # ------------------------------------------------------------------

    def _execute_cycle(
        self,
        db: Session,
        run,
        portfolio_id: UUID,
        mode: str,
        now: datetime,
        warnings: list[str],
    ) -> OrchestrationResult:

        # NAV safety check
        try:
            valuation = self._valuation_service.value_portfolio(db, portfolio_id)
            nav = Decimal(valuation.nav)
        except Exception:
            nav = ZERO
            warnings.append("Portfolio valuation could not be computed")

        if nav == ZERO:
            self._run_repo.update(db, run, data={
                "status": OrchestrationStatus.ABORTED,
                "abort_reason": "NAV is zero",
                "completed_at": datetime.now(timezone.utc),
            })
            return OrchestrationResult(
                run_id=run.id,
                portfolio_id=portfolio_id,
                mode=mode,
                status=OrchestrationStatus.ABORTED,
                signals_detected=0,
                actions_taken=0,
                rebalance_preview_id=None,
                abort_reason="NAV is zero",
                warnings=warnings,
            )

        eval_result = self._strategy_service.evaluate_portfolio_strategies(
            db, portfolio_id,
        )

        signals_detected = eval_result.strategies_evaluated
        warnings.extend(eval_result.warnings)

        has_rebalance_action = any(
            s.action_type in (
                StrategyActionType.CREATE_REBALANCE_PREVIEW,
                "create_rebalance_preview",
            )
            for s in eval_result.signals
        )

        preview_id = None
        actions_taken = 0
        run_metadata: dict = {}

        if mode == RebalanceExecutionMode.MANUAL:
            pass
        elif has_rebalance_action:
            try:
                preview = self._drift_service.create_rebalance_plan(
                    db, portfolio_id,
                )
                preview_id = preview.id
                actions_taken = 1
            except Exception as exc:
                warnings.append(f"Rebalance plan creation failed: {exc}")

        if mode == RebalanceExecutionMode.AUTOMATIC and preview_id is not None:
            run_metadata["execution_eligible"] = True

        self._run_repo.update(db, run, data={
            "signals_detected": signals_detected,
            "actions_taken": actions_taken,
            "rebalance_preview_id": preview_id,
            "status": OrchestrationStatus.COMPLETED,
            "completed_at": datetime.now(timezone.utc),
            "metadata_": run_metadata,
        })

        return OrchestrationResult(
            run_id=run.id,
            portfolio_id=portfolio_id,
            mode=mode,
            status=OrchestrationStatus.COMPLETED,
            signals_detected=signals_detected,
            actions_taken=actions_taken,
            rebalance_preview_id=preview_id,
            abort_reason=None,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_mode(db: Session, portfolio_id: UUID) -> str:
        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio_id)
            .first()
        )
        if policy is None:
            return RebalanceExecutionMode.MANUAL

        params = policy.parameters or {}
        raw = params.get("orchestration_mode")
        if raw in (
            RebalanceExecutionMode.MANUAL,
            RebalanceExecutionMode.ASSISTED,
            RebalanceExecutionMode.AUTOMATIC,
        ):
            return raw
        return RebalanceExecutionMode.MANUAL
