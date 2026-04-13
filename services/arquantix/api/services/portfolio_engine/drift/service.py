"""Drift Detection & Rebalance Engine (Phase 6).

Read-only computation engine. Never modifies:
- orders, executions, trades, settlements, ledger, positions, valuations.

create_rebalance_plan() persists via the existing RebalancePreviewService.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..allocations.models import TargetAllocation
from ..assets.models import Asset
from ..instruments.models import Instrument
from ..rebalancing.models import RebalancePolicy
from ..rebalance_preview.enums import TradeDirection
from ..rebalance_preview.schemas import PreviewCreate, PreviewItemCreate
from ..rebalance_preview.service import RebalancePreviewService
from ..valuations.schemas import PortfolioValuationResponse
from ..valuations.service import ValuationService
from .schemas import (
    DriftItemResult,
    DriftReport,
    RebalancePreviewResponse,
    RebalanceTradeItem,
)

ZERO = Decimal("0")
DEFAULT_THRESHOLD = Decimal("0.05")


class PortfolioNotFoundForDriftError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class DriftRebalanceService:

    def __init__(self) -> None:
        self._valuation_service = ValuationService()
        self._preview_service = RebalancePreviewService()

    # ------------------------------------------------------------------
    # detect_drift
    # ------------------------------------------------------------------

    def detect_drift(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        threshold: Optional[Decimal] = None,
        valuation: Optional[PortfolioValuationResponse] = None,
    ) -> DriftReport:
        if valuation is None:
            try:
                valuation = self._valuation_service.value_portfolio(db, portfolio_id)
            except Exception:
                raise PortfolioNotFoundForDriftError(portfolio_id)

        nav = Decimal(valuation.nav)
        warnings: list[str] = []

        effective_threshold = self._resolve_threshold(db, portfolio_id, threshold)

        target_allocations = (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio_id)
            .all()
        )

        if not target_allocations:
            warnings.append("Portfolio has no target allocations; drift detection skipped")
            return DriftReport(
                portfolio_id=portfolio_id,
                nav=str(nav),
                threshold=str(effective_threshold),
                max_absolute_drift="0",
                drift_score="0",
                needs_rebalance=False,
                priced_positions_count=valuation.priced_positions_count,
                unpriced_excluded_count=valuation.unpriced_positions_count,
                warnings=warnings,
                items=[],
            )

        if nav == ZERO:
            warnings.append("Portfolio NAV is 0; drift cannot be calculated")
            return DriftReport(
                portfolio_id=portfolio_id,
                nav="0",
                threshold=str(effective_threshold),
                max_absolute_drift="0",
                drift_score="0",
                needs_rebalance=False,
                priced_positions_count=0,
                unpriced_excluded_count=valuation.unpriced_positions_count,
                warnings=warnings,
                items=[],
            )

        priced_positions = {
            p.instrument_id: p
            for p in valuation.positions
            if p.pricing_status == "priced"
        }
        target_instrument_ids = {ta.instrument_id for ta in target_allocations}

        items: list[DriftItemResult] = []
        max_abs_drift = ZERO
        sum_abs_drift = ZERO

        for ta in target_allocations:
            target_w = Decimal(str(ta.target_weight))
            pos = priced_positions.get(ta.instrument_id)
            current_w = Decimal(pos.allocation_weight) if pos and pos.allocation_weight else ZERO
            drift = current_w - target_w

            abs_drift = abs(drift)
            max_abs_drift = max(max_abs_drift, abs_drift)
            sum_abs_drift += abs_drift

            instrument, asset_symbol = self._resolve_instrument(db, ta.instrument_id)

            items.append(DriftItemResult(
                instrument_id=ta.instrument_id,
                instrument_code=instrument.code if instrument else "UNKNOWN",
                asset_symbol=asset_symbol,
                target_weight=str(target_w),
                current_weight=str(current_w),
                drift=str(drift),
                exceeds_threshold=abs_drift > effective_threshold,
                is_unallocated=False,
            ))

        for instr_id, pos in priced_positions.items():
            if instr_id not in target_instrument_ids:
                current_w = Decimal(pos.allocation_weight) if pos.allocation_weight else ZERO
                drift = current_w
                abs_drift = abs(drift)
                max_abs_drift = max(max_abs_drift, abs_drift)
                sum_abs_drift += abs_drift

                instrument, asset_symbol = self._resolve_instrument(db, instr_id)

                items.append(DriftItemResult(
                    instrument_id=instr_id,
                    instrument_code=instrument.code if instrument else "UNKNOWN",
                    asset_symbol=asset_symbol,
                    target_weight="0",
                    current_weight=str(current_w),
                    drift=str(drift),
                    exceeds_threshold=abs_drift > effective_threshold,
                    is_unallocated=True,
                ))

        drift_score = (sum_abs_drift / Decimal("2")).quantize(Decimal("0.000001"))
        needs_rebalance = any(item.exceeds_threshold for item in items)

        if valuation.unpriced_positions_count > 0:
            warnings.append(
                f"{valuation.unpriced_positions_count} unpriced position(s) excluded from drift calculation"
            )

        return DriftReport(
            portfolio_id=portfolio_id,
            nav=str(nav),
            threshold=str(effective_threshold),
            max_absolute_drift=str(max_abs_drift),
            drift_score=str(drift_score),
            needs_rebalance=needs_rebalance,
            priced_positions_count=valuation.priced_positions_count,
            unpriced_excluded_count=valuation.unpriced_positions_count,
            warnings=warnings,
            items=items,
        )

    # ------------------------------------------------------------------
    # generate_rebalance_preview
    # ------------------------------------------------------------------

    def generate_rebalance_preview(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        threshold: Optional[Decimal] = None,
        valuation: Optional[PortfolioValuationResponse] = None,
    ) -> RebalancePreviewResponse:
        if valuation is None:
            try:
                valuation = self._valuation_service.value_portfolio(db, portfolio_id)
            except Exception:
                raise PortfolioNotFoundForDriftError(portfolio_id)

        nav = Decimal(valuation.nav)
        warnings: list[str] = []
        effective_threshold = self._resolve_threshold(db, portfolio_id, threshold)

        target_allocations = (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio_id)
            .all()
        )

        if not target_allocations:
            warnings.append("Portfolio has no target allocations; rebalance preview skipped")
            return RebalancePreviewResponse(
                portfolio_id=portfolio_id,
                nav=str(nav),
                threshold=str(effective_threshold),
                needs_rebalance=False,
                drift_score="0",
                warnings=warnings,
                trades=[],
            )

        if nav == ZERO:
            warnings.append("Portfolio NAV is 0; rebalance preview cannot be generated")
            return RebalancePreviewResponse(
                portfolio_id=portfolio_id,
                nav="0",
                threshold=str(effective_threshold),
                needs_rebalance=False,
                drift_score="0",
                warnings=warnings,
                trades=[],
            )

        min_trade_size = self._resolve_min_trade_size(db, portfolio_id)

        priced_positions = {
            p.instrument_id: p
            for p in valuation.positions
            if p.pricing_status == "priced"
        }
        target_instrument_ids = {ta.instrument_id for ta in target_allocations}

        trades: list[RebalanceTradeItem] = []
        sum_abs_drift = ZERO
        any_exceeds = False

        for ta in target_allocations:
            target_w = Decimal(str(ta.target_weight))
            pos = priced_positions.get(ta.instrument_id)
            current_w = Decimal(pos.allocation_weight) if pos and pos.allocation_weight else ZERO
            drift = current_w - target_w

            abs_drift = abs(drift)
            sum_abs_drift += abs_drift
            if abs_drift > effective_threshold:
                any_exceeds = True

            target_value = nav * target_w
            current_value = Decimal(pos.market_value) if pos and pos.market_value else ZERO
            delta = target_value - current_value

            price_str = pos.price if pos else None
            price_dec = Decimal(price_str) if price_str else None

            action, trade_value, trade_qty = self._compute_trade(
                delta, price_dec, min_trade_size
            )

            instrument, asset_symbol = self._resolve_instrument(db, ta.instrument_id)

            trades.append(RebalanceTradeItem(
                instrument_id=ta.instrument_id,
                instrument_code=instrument.code if instrument else "UNKNOWN",
                asset_symbol=asset_symbol,
                target_weight=str(target_w),
                current_weight=str(current_w),
                drift=str(drift),
                action=action,
                trade_value=str(trade_value) if trade_value is not None else None,
                trade_quantity=str(trade_qty) if trade_qty is not None else None,
                price=str(price_dec) if price_dec is not None else None,
            ))

        for instr_id, pos in priced_positions.items():
            if instr_id not in target_instrument_ids:
                current_w = Decimal(pos.allocation_weight) if pos.allocation_weight else ZERO
                drift = current_w
                sum_abs_drift += abs(drift)
                if abs(drift) > effective_threshold:
                    any_exceeds = True

                current_value = Decimal(pos.market_value) if pos.market_value else ZERO
                delta = ZERO - current_value
                price_dec = Decimal(pos.price) if pos.price else None

                action, trade_value, trade_qty = self._compute_trade(
                    delta, price_dec, min_trade_size
                )

                instrument, asset_symbol = self._resolve_instrument(db, instr_id)

                trades.append(RebalanceTradeItem(
                    instrument_id=instr_id,
                    instrument_code=instrument.code if instrument else "UNKNOWN",
                    asset_symbol=asset_symbol,
                    target_weight="0",
                    current_weight=str(current_w),
                    drift=str(drift),
                    action=action,
                    trade_value=str(trade_value) if trade_value is not None else None,
                    trade_quantity=str(trade_qty) if trade_qty is not None else None,
                    price=str(price_dec) if price_dec is not None else None,
                ))

        drift_score = (sum_abs_drift / Decimal("2")).quantize(Decimal("0.000001"))

        if valuation.unpriced_positions_count > 0:
            warnings.append(
                f"{valuation.unpriced_positions_count} unpriced position(s) excluded from rebalance"
            )

        return RebalancePreviewResponse(
            portfolio_id=portfolio_id,
            nav=str(nav),
            threshold=str(effective_threshold),
            needs_rebalance=any_exceeds,
            drift_score=str(drift_score),
            warnings=warnings,
            trades=trades,
        )

    # ------------------------------------------------------------------
    # create_rebalance_plan (persisted)
    # ------------------------------------------------------------------

    def create_rebalance_plan(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        threshold: Optional[Decimal] = None,
    ):
        valuation = self._valuation_service.value_portfolio(db, portfolio_id)
        preview_response = self.generate_rebalance_preview(
            db, portfolio_id, threshold=threshold, valuation=valuation,
        )

        preview_items = []
        for trade in preview_response.trades:
            if trade.action == "buy":
                direction = TradeDirection.BUY
            elif trade.action == "sell":
                direction = TradeDirection.SELL
            else:
                direction = TradeDirection.HOLD

            preview_items.append(PreviewItemCreate(
                instrument_id=trade.instrument_id,
                current_weight=Decimal(trade.current_weight) if trade.current_weight else None,
                target_weight=Decimal(trade.target_weight) if trade.target_weight else None,
                drift=Decimal(trade.drift) if trade.drift else None,
                trade_required=Decimal(trade.trade_value) if trade.trade_value else None,
                trade_direction=direction,
                estimated_trade_size=Decimal(trade.trade_quantity) if trade.trade_quantity else None,
            ))

        payload = PreviewCreate(
            portfolio_id=portfolio_id,
            drift_score=Decimal(preview_response.drift_score),
            status="completed",
            parameters={
                "threshold": str(preview_response.threshold),
                "nav": str(preview_response.nav),
                "source": "drift_engine_v1",
            },
            items=preview_items,
        )

        preview = self._preview_service.create_preview(db, payload)
        return preview

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_threshold(
        db: Session, portfolio_id: UUID, explicit: Optional[Decimal]
    ) -> Decimal:
        if explicit is not None:
            return explicit
        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio_id)
            .first()
        )
        if policy and policy.drift_threshold is not None:
            return Decimal(str(policy.drift_threshold))
        return DEFAULT_THRESHOLD

    @staticmethod
    def _resolve_min_trade_size(db: Session, portfolio_id: UUID) -> Decimal:
        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio_id)
            .first()
        )
        if policy and policy.min_trade_size is not None:
            return Decimal(str(policy.min_trade_size))
        return ZERO

    @staticmethod
    def _resolve_instrument(
        db: Session, instrument_id: UUID
    ) -> tuple[Optional[Instrument], Optional[str]]:
        instrument = (
            db.query(Instrument)
            .filter(Instrument.id == instrument_id)
            .first()
        )
        asset_symbol = None
        if instrument and instrument.asset_id:
            asset = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
            asset_symbol = asset.symbol if asset else None
        return instrument, asset_symbol

    @staticmethod
    def _compute_trade(
        delta: Decimal,
        price: Optional[Decimal],
        min_trade_size: Decimal,
    ) -> tuple[str, Optional[Decimal], Optional[Decimal]]:
        """Returns (action, trade_value, trade_quantity)."""
        abs_delta = abs(delta)

        if abs_delta < min_trade_size and min_trade_size > ZERO:
            return "hold", None, None

        if delta > ZERO:
            action = "buy"
        elif delta < ZERO:
            action = "sell"
        else:
            return "hold", None, None

        trade_value = abs_delta.quantize(Decimal("0.01"))
        trade_qty = None
        if price and price > ZERO:
            trade_qty = (abs_delta / price).quantize(Decimal("0.0000000001"))

        return action, trade_value, trade_qty
