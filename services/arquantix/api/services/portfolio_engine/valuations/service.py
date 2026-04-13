"""Valuation & Performance Engine (Phase 5).

Read-only derived logic. Never modifies:
- trades, settlements, ledger entries, position atoms, orders, executions.

On-demand valuation is purely ephemeral (no DB writes).
Snapshots persist to pe_portfolio_valuations / pe_position_valuations (append-only).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from ..assets.models import Asset
from ..instruments.models import Instrument
from ..instruments.price_bridge import (
    MarketDataLinkMissingError,
    QuoteNotAvailableError,
    get_instrument_price,
)
from ..portfolios.models import Portfolio
from ..positions.models import PositionAtom
from .enums import PricingStatus, ValuationSource
from .repository import ValuationRepository
from .schemas import (
    PortfolioValuationResponse,
    PortfolioValuationSnapshotRead,
    PositionValuationResult,
)

ZERO = Decimal("0")


class PortfolioNotFoundForValuationError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class PositionNotFoundForValuationError(Exception):
    def __init__(self, position_id: UUID):
        self.position_id = position_id
        super().__init__(f"Position {position_id} not found")


class ValuationService:

    def __init__(self) -> None:
        self._repo = ValuationRepository()

    # ------------------------------------------------------------------
    # On-demand single position valuation
    # ------------------------------------------------------------------

    def value_position(
        self, db: Session, position_id: UUID
    ) -> PositionValuationResult:
        position = (
            db.query(PositionAtom)
            .filter(PositionAtom.id == position_id)
            .first()
        )
        if position is None:
            raise PositionNotFoundForValuationError(position_id)

        now = datetime.now(timezone.utc)
        warnings: list[str] = []
        instrument, asset_symbol = self._resolve_instrument(db, position.instrument_id)
        instrument_code = instrument.code if instrument else "UNKNOWN"

        price_dec, market_value_dec, unrealized_dec, pricing_status = (
            self._compute_position_metrics(db, position, warnings)
        )

        return PositionValuationResult(
            position_id=position.id,
            instrument_id=position.instrument_id,
            instrument_code=instrument_code,
            asset_symbol=asset_symbol,
            position_type=position.position_type,
            quantity=str(position.quantity),
            average_entry_price=str(position.average_entry_price) if position.average_entry_price is not None else None,
            price=str(price_dec) if price_dec is not None else None,
            market_value=str(market_value_dec) if market_value_dec is not None else None,
            unrealized_pnl=str(unrealized_dec) if unrealized_dec is not None else None,
            realized_pnl=str(position.realized_pnl or ZERO),
            allocation_weight=None,
            pricing_status=pricing_status,
            valuation_timestamp=now,
        )

    # ------------------------------------------------------------------
    # On-demand portfolio valuation
    # ------------------------------------------------------------------

    def value_portfolio(
        self, db: Session, portfolio_id: UUID
    ) -> PortfolioValuationResponse:
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id)
            .first()
        )
        if portfolio is None:
            raise PortfolioNotFoundForValuationError(portfolio_id)

        now = datetime.now(timezone.utc)
        warnings: list[str] = []

        open_positions = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.status == "open",
            )
            .all()
        )

        total_realized_all = self._aggregate_realized_pnl(db, portfolio_id)

        position_results: list[dict] = []
        total_nav = ZERO
        total_unrealized = ZERO
        priced_count = 0
        unpriced_count = 0
        missing_avg_count = 0

        for pos in open_positions:
            instrument, asset_symbol = self._resolve_instrument(db, pos.instrument_id)
            instrument_code = instrument.code if instrument else "UNKNOWN"

            price_dec, market_value_dec, unrealized_dec, pricing_status = (
                self._compute_position_metrics(db, pos, warnings)
            )

            if pricing_status == PricingStatus.PRICED:
                priced_count += 1
                total_nav += market_value_dec
                total_unrealized += unrealized_dec
                if pos.average_entry_price is None and unrealized_dec == ZERO:
                    missing_avg_count += 1
            else:
                unpriced_count += 1

            position_results.append({
                "position_id": pos.id,
                "instrument_id": pos.instrument_id,
                "instrument_code": instrument_code,
                "asset_symbol": asset_symbol,
                "position_type": pos.position_type,
                "quantity": str(pos.quantity),
                "average_entry_price": str(pos.average_entry_price) if pos.average_entry_price is not None else None,
                "price": str(price_dec) if price_dec is not None else None,
                "market_value": str(market_value_dec) if market_value_dec is not None else None,
                "unrealized_pnl": str(unrealized_dec) if unrealized_dec is not None else None,
                "realized_pnl": str(pos.realized_pnl or ZERO),
                "allocation_weight": None,
                "pricing_status": pricing_status,
                "valuation_timestamp": now,
            })

        for row in position_results:
            if row["pricing_status"] == PricingStatus.PRICED and total_nav > ZERO:
                mv = Decimal(row["market_value"])
                weight = (mv / total_nav).quantize(Decimal("0.000001"))
                row["allocation_weight"] = str(weight)

        if unpriced_count > 0:
            noun = "position" if unpriced_count == 1 else "positions"
            warnings.append(
                f"{unpriced_count} {noun} could not be priced "
                f"because no market quote link is available"
            )

        if missing_avg_count > 0:
            noun = "position" if missing_avg_count == 1 else "positions"
            warnings.append(
                f"{missing_avg_count} priced {noun} has no average entry price; "
                f"unrealized pnl was set to 0"
            )

        total_pnl = total_realized_all + total_unrealized

        positions = [PositionValuationResult(**row) for row in position_results]

        return PortfolioValuationResponse(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            base_currency=portfolio.base_currency,
            nav=str(total_nav),
            total_realized_pnl=str(total_realized_all),
            total_unrealized_pnl=str(total_unrealized),
            total_pnl=str(total_pnl),
            priced_positions_count=priced_count,
            unpriced_positions_count=unpriced_count,
            warnings=warnings,
            positions=positions,
            valuation_timestamp=now,
        )

    # ------------------------------------------------------------------
    # Snapshot creation (persisted)
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        source: str = ValuationSource.ON_DEMAND,
    ) -> PortfolioValuationSnapshotRead:
        valuation = self.value_portfolio(db, portfolio_id)
        ts = valuation.valuation_timestamp

        for pos_val in valuation.positions:
            self._repo.create_position_valuation(db, data={
                "position_id": pos_val.position_id,
                "portfolio_id": portfolio_id,
                "instrument_id": pos_val.instrument_id,
                "quantity": Decimal(pos_val.quantity),
                "price": Decimal(pos_val.price) if pos_val.price else None,
                "market_value": Decimal(pos_val.market_value) if pos_val.market_value else None,
                "average_entry_price": Decimal(pos_val.average_entry_price) if pos_val.average_entry_price else None,
                "unrealized_pnl": Decimal(pos_val.unrealized_pnl) if pos_val.unrealized_pnl else None,
                "realized_pnl": Decimal(pos_val.realized_pnl),
                "pricing_status": pos_val.pricing_status,
                "valuation_timestamp": ts,
            })

        pv = self._repo.create_portfolio_valuation(db, data={
            "portfolio_id": portfolio_id,
            "nav": Decimal(valuation.nav),
            "total_realized_pnl": Decimal(valuation.total_realized_pnl),
            "total_unrealized_pnl": Decimal(valuation.total_unrealized_pnl),
            "total_pnl": Decimal(valuation.total_pnl),
            "priced_positions_count": valuation.priced_positions_count,
            "unpriced_positions_count": valuation.unpriced_positions_count,
            "valuation_source": source,
            "valuation_timestamp": ts,
            "metadata_": {},
        })

        return PortfolioValuationSnapshotRead.model_validate(pv)

    # ------------------------------------------------------------------
    # Snapshot history
    # ------------------------------------------------------------------

    def list_snapshots(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PortfolioValuationSnapshotRead], int]:
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id)
            .first()
        )
        if portfolio is None:
            raise PortfolioNotFoundForValuationError(portfolio_id)

        items, total = self._repo.list_portfolio_snapshots(
            db, portfolio_id, skip=skip, limit=limit,
        )
        return [PortfolioValuationSnapshotRead.model_validate(i) for i in items], total

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
    def _compute_position_metrics(
        db: Session,
        position: PositionAtom,
        warnings: list[str],
    ) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal], str]:
        """Returns (price, market_value, unrealized_pnl, pricing_status)."""
        if position.position_type != "spot":
            return None, None, None, PricingStatus.UNPRICED

        try:
            result = get_instrument_price(db, position.instrument_id)
        except (MarketDataLinkMissingError, QuoteNotAvailableError):
            return None, None, None, PricingStatus.UNPRICED

        price_str = result.get("price")
        if price_str is None:
            return None, None, None, PricingStatus.UNPRICED

        price_dec = Decimal(price_str)
        quantity = Decimal(str(position.quantity)) if position.quantity is not None else ZERO
        market_value = (price_dec * quantity).quantize(Decimal("0.01"))

        avg_price = position.average_entry_price
        if avg_price is not None and avg_price > 0:
            unrealized = (quantity * (price_dec - Decimal(str(avg_price)))).quantize(Decimal("0.01"))
        else:
            unrealized = ZERO

        return price_dec, market_value, unrealized, PricingStatus.PRICED

    @staticmethod
    def _aggregate_realized_pnl(db: Session, portfolio_id: UUID) -> Decimal:
        """Sum realized_pnl across ALL positions (open + closed) for the portfolio."""
        result = (
            db.query(sa_func.coalesce(sa_func.sum(PositionAtom.realized_pnl), 0))
            .filter(PositionAtom.portfolio_id == portfolio_id)
            .scalar()
        )
        return Decimal(str(result))
