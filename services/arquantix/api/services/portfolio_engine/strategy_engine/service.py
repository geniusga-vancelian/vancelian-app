"""Strategy Engine (Phase 7).

Decision layer only. Evaluates strategies, produces signals/actions, logs them.
Never modifies: orders, executions, trades, settlements, ledger, positions, valuations, drift.

May optionally create a rebalance preview via DriftRebalanceService.create_rebalance_plan().
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..drift.service import DriftRebalanceService, PortfolioNotFoundForDriftError
from ..portfolios.models import Portfolio
from ..rebalancing.models import RebalancePolicy
from ..risk.models import RiskPolicy
from ..strategies.models import StrategyInstance
from ..valuations.schemas import PortfolioValuationResponse
from ..valuations.service import ValuationService
from .enums import SignalSeverity, StrategyActionType, StrategySignalType
from .models import StrategyEvaluation
from .repository import StrategyEvaluationRepository
from .schemas import PortfolioEvaluationResponse, StrategySignalResult

ZERO = Decimal("0")

FREQUENCY_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "yearly": 365,
}


class PortfolioNotFoundForStrategyError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class StrategyInstanceNotFoundError(Exception):
    def __init__(self, instance_id: UUID):
        self.instance_id = instance_id
        super().__init__(f"StrategyInstance {instance_id} not found")


class StrategyEngineService:

    def __init__(self) -> None:
        self._valuation_service = ValuationService()
        self._drift_service = DriftRebalanceService()
        self._eval_repo = StrategyEvaluationRepository()

    # ------------------------------------------------------------------
    # evaluate_portfolio_strategies
    # ------------------------------------------------------------------

    def evaluate_portfolio_strategies(
        self, db: Session, portfolio_id: UUID
    ) -> PortfolioEvaluationResponse:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise PortfolioNotFoundForStrategyError(portfolio_id)

        now = datetime.now(timezone.utc)
        warnings: list[str] = []

        instances = (
            db.query(StrategyInstance)
            .filter(
                StrategyInstance.portfolio_id == portfolio_id,
                StrategyInstance.status == "active",
            )
            .order_by(StrategyInstance.priority.asc())
            .all()
        )

        if not instances:
            return PortfolioEvaluationResponse(
                portfolio_id=portfolio_id,
                evaluated_at=now,
                strategies_evaluated=0,
                signals=[],
                warnings=["Portfolio has no active strategies"],
            )

        valuation = self._safe_valuation(db, portfolio_id, warnings)

        signals: list[StrategySignalResult] = []
        for instance in instances:
            definition = instance.definition
            if definition is None:
                warnings.append(
                    f"StrategyInstance {instance.id} has no linked definition"
                )
                continue

            signal = self._evaluate_strategy(
                db, instance, definition.strategy_type, valuation, now, warnings
            )
            signals.append(signal)

            self._eval_repo.create(db, data={
                "portfolio_id": portfolio_id,
                "strategy_instance_id": instance.id,
                "strategy_type": definition.strategy_type,
                "signal_type": signal.signal_type,
                "action_type": signal.action_type,
                "severity": signal.severity,
                "details": signal.details,
                "evaluation_timestamp": now,
            })

        return PortfolioEvaluationResponse(
            portfolio_id=portfolio_id,
            evaluated_at=now,
            strategies_evaluated=len(signals),
            signals=signals,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # execute_strategy_action
    # ------------------------------------------------------------------

    def execute_strategy_action(
        self, db: Session, strategy_instance_id: UUID
    ) -> PortfolioEvaluationResponse:
        instance = (
            db.query(StrategyInstance)
            .filter(StrategyInstance.id == strategy_instance_id)
            .first()
        )
        if instance is None:
            raise StrategyInstanceNotFoundError(strategy_instance_id)

        portfolio_id = instance.portfolio_id
        now = datetime.now(timezone.utc)
        warnings: list[str] = []
        valuation = self._safe_valuation(db, portfolio_id, warnings)

        definition = instance.definition
        if definition is None:
            warnings.append(
                f"StrategyInstance {instance.id} has no linked definition"
            )
            return PortfolioEvaluationResponse(
                portfolio_id=portfolio_id,
                evaluated_at=now,
                strategies_evaluated=0,
                signals=[],
                warnings=warnings,
            )

        signal = self._evaluate_strategy(
            db, instance, definition.strategy_type, valuation, now, warnings
        )

        self._eval_repo.create(db, data={
            "portfolio_id": portfolio_id,
            "strategy_instance_id": instance.id,
            "strategy_type": definition.strategy_type,
            "signal_type": signal.signal_type,
            "action_type": signal.action_type,
            "severity": signal.severity,
            "details": signal.details,
            "evaluation_timestamp": now,
        })

        if signal.action_type == StrategyActionType.CREATE_REBALANCE_PREVIEW:
            try:
                self._drift_service.create_rebalance_plan(db, portfolio_id)
            except Exception as exc:
                warnings.append(f"Rebalance plan creation failed: {exc}")

        return PortfolioEvaluationResponse(
            portfolio_id=portfolio_id,
            evaluated_at=now,
            strategies_evaluated=1,
            signals=[signal],
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _evaluate_strategy(
        self,
        db: Session,
        instance: StrategyInstance,
        strategy_type: str,
        valuation: Optional[PortfolioValuationResponse],
        now: datetime,
        warnings: list[str],
    ) -> StrategySignalResult:
        if strategy_type == "threshold_rebalance":
            return self._eval_threshold_rebalance(db, instance, valuation, warnings)
        elif strategy_type == "periodic_rebalance":
            return self._eval_periodic_rebalance(db, instance, now, warnings)
        elif strategy_type == "drift_guard":
            return self._eval_drift_guard(db, instance, valuation, warnings)
        elif strategy_type == "risk_limit":
            return self._eval_risk_limit(db, instance, valuation, warnings)
        else:
            return self._no_signal(instance, strategy_type, details={
                "reason": f"Unsupported strategy type: {strategy_type}",
            })

    # ------------------------------------------------------------------
    # Evaluator: threshold_rebalance
    # ------------------------------------------------------------------

    def _eval_threshold_rebalance(
        self,
        db: Session,
        instance: StrategyInstance,
        valuation: Optional[PortfolioValuationResponse],
        warnings: list[str],
    ) -> StrategySignalResult:
        params = instance.parameters or {}
        threshold = Decimal(str(params.get("threshold", "0.05")))

        try:
            drift_report = self._drift_service.detect_drift(
                db, instance.portfolio_id,
                threshold=threshold,
                valuation=valuation,
            )
        except PortfolioNotFoundForDriftError:
            warnings.append("Drift detection failed for threshold_rebalance")
            return self._no_signal(instance, "threshold_rebalance")

        details = {
            "threshold": str(threshold),
            "max_absolute_drift": drift_report.max_absolute_drift,
            "drift_score": drift_report.drift_score,
            "needs_rebalance": drift_report.needs_rebalance,
        }

        if drift_report.needs_rebalance:
            return StrategySignalResult(
                strategy_instance_id=instance.id,
                strategy_type="threshold_rebalance",
                signal_type=StrategySignalType.REBALANCE_REQUIRED,
                action_type=StrategyActionType.CREATE_REBALANCE_PREVIEW,
                severity=SignalSeverity.WARNING,
                details=details,
            )

        return self._no_signal(instance, "threshold_rebalance", details=details)

    # ------------------------------------------------------------------
    # Evaluator: periodic_rebalance
    # ------------------------------------------------------------------

    def _eval_periodic_rebalance(
        self,
        db: Session,
        instance: StrategyInstance,
        now: datetime,
        warnings: list[str],
    ) -> StrategySignalResult:
        # TODO: v1 approximation — uses last evaluation log as reference.
        # Future versions should use actual last rebalance execution date
        # (e.g., last trade/plan linked to rebalancing) instead of evaluation history.
        params = instance.parameters or {}
        frequency = params.get("frequency", "monthly")
        interval_days = FREQUENCY_DAYS.get(frequency, 30)

        last_eval = self._eval_repo.get_latest_by_instance(
            db, instance.id,
            signal_type=StrategySignalType.PERIODIC_REBALANCE,
        )

        if last_eval is not None:
            elapsed = now - last_eval.evaluation_timestamp
            days_since = elapsed.days
        else:
            days_since = interval_days + 1

        details = {
            "frequency": frequency,
            "interval_days": interval_days,
            "days_since_last_reference": days_since,
        }

        if days_since >= interval_days:
            return StrategySignalResult(
                strategy_instance_id=instance.id,
                strategy_type="periodic_rebalance",
                signal_type=StrategySignalType.PERIODIC_REBALANCE,
                action_type=StrategyActionType.CREATE_REBALANCE_PREVIEW,
                severity=SignalSeverity.INFO,
                details=details,
            )

        return self._no_signal(instance, "periodic_rebalance", details=details)

    # ------------------------------------------------------------------
    # Evaluator: drift_guard
    # ------------------------------------------------------------------

    def _eval_drift_guard(
        self,
        db: Session,
        instance: StrategyInstance,
        valuation: Optional[PortfolioValuationResponse],
        warnings: list[str],
    ) -> StrategySignalResult:
        params = instance.parameters or {}
        warning_threshold = Decimal(str(params.get("warning_threshold", "0.03")))

        try:
            drift_report = self._drift_service.detect_drift(
                db, instance.portfolio_id, valuation=valuation,
            )
        except PortfolioNotFoundForDriftError:
            warnings.append("Drift detection failed for drift_guard")
            return self._no_signal(instance, "drift_guard")

        max_drift = Decimal(drift_report.max_absolute_drift)

        details = {
            "warning_threshold": str(warning_threshold),
            "max_absolute_drift": str(max_drift),
            "drift_score": drift_report.drift_score,
        }

        if max_drift > warning_threshold:
            return StrategySignalResult(
                strategy_instance_id=instance.id,
                strategy_type="drift_guard",
                signal_type=StrategySignalType.DRIFT_WARNING,
                action_type=StrategyActionType.NO_ACTION,
                severity=SignalSeverity.WARNING,
                details=details,
            )

        return self._no_signal(instance, "drift_guard", details=details)

    # ------------------------------------------------------------------
    # Evaluator: risk_limit
    # ------------------------------------------------------------------

    def _eval_risk_limit(
        self,
        db: Session,
        instance: StrategyInstance,
        valuation: Optional[PortfolioValuationResponse],
        warnings: list[str],
    ) -> StrategySignalResult:
        risk_policy = (
            db.query(RiskPolicy)
            .filter(RiskPolicy.portfolio_id == instance.portfolio_id)
            .first()
        )

        if risk_policy is None:
            warnings.append("No RiskPolicy found for portfolio; skipping risk_limit evaluation")
            return self._no_signal(instance, "risk_limit", details={
                "reason": "no_risk_policy",
            })

        if valuation is None:
            return self._no_signal(instance, "risk_limit", details={
                "reason": "no_valuation_available",
            })

        max_asset_w = (
            Decimal(str(risk_policy.max_asset_weight))
            if risk_policy.max_asset_weight is not None
            else None
        )
        max_position_w = (
            Decimal(str(risk_policy.max_position_weight))
            if risk_policy.max_position_weight is not None
            else None
        )

        breached: list[dict] = []
        for pos in valuation.positions:
            if pos.pricing_status != "priced" or pos.allocation_weight is None:
                continue
            weight = Decimal(pos.allocation_weight)
            if max_asset_w is not None and weight > max_asset_w:
                breached.append({
                    "instrument_id": str(pos.instrument_id),
                    "instrument_code": pos.instrument_code,
                    "weight": str(weight),
                    "limit": str(max_asset_w),
                    "limit_type": "max_asset_weight",
                })
            if max_position_w is not None and weight > max_position_w:
                breached.append({
                    "instrument_id": str(pos.instrument_id),
                    "instrument_code": pos.instrument_code,
                    "weight": str(weight),
                    "limit": str(max_position_w),
                    "limit_type": "max_position_weight",
                })

        details = {
            "max_asset_weight": str(max_asset_w) if max_asset_w else None,
            "max_position_weight": str(max_position_w) if max_position_w else None,
            "breached_instruments": breached,
        }

        if breached:
            return StrategySignalResult(
                strategy_instance_id=instance.id,
                strategy_type="risk_limit",
                signal_type=StrategySignalType.RISK_LIMIT_EXCEEDED,
                action_type=StrategyActionType.ALERT_RISK,
                severity=SignalSeverity.CRITICAL,
                details=details,
            )

        return self._no_signal(instance, "risk_limit", details=details)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_valuation(
        self,
        db: Session,
        portfolio_id: UUID,
        warnings: list[str],
    ) -> Optional[PortfolioValuationResponse]:
        try:
            return self._valuation_service.value_portfolio(db, portfolio_id)
        except Exception:
            warnings.append("Portfolio valuation could not be computed")
            return None

    @staticmethod
    def _no_signal(
        instance: StrategyInstance,
        strategy_type: str,
        *,
        details: Optional[dict] = None,
    ) -> StrategySignalResult:
        return StrategySignalResult(
            strategy_instance_id=instance.id,
            strategy_type=strategy_type,
            signal_type=StrategySignalType.NO_SIGNAL,
            action_type=StrategyActionType.NO_ACTION,
            severity=SignalSeverity.INFO,
            details=details or {},
        )
