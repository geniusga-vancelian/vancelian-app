"""Read-only service that computes a live portfolio summary from current positions
and the existing PE instrument price bridge.

No DB writes.  No caching.  No snapshots.  No FX conversion.
"""
from __future__ import annotations
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from ..assets.models import Asset
from ..instruments.models import Instrument
from ..instruments.price_bridge import (
    MarketDataLinkMissingError,
    QuoteNotAvailableError,
    get_instrument_price,
)
from ..portfolios.models import Portfolio
from ..positions.models import PositionAtom
from .schemas import PortfolioSummaryResponse, PositionSummary

ZERO = Decimal("0")


class PortfolioNotFoundForSummaryError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class PortfolioSummaryService:

    def get_summary(self, db: Session, portfolio_id: UUID) -> PortfolioSummaryResponse:
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id)
            .first()
        )
        if portfolio is None:
            raise PortfolioNotFoundForSummaryError(portfolio_id)

        open_positions = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.status == "open",
            )
            .all()
        )

        position_rows: list[dict] = []
        warnings: list[str] = []
        total_market_value = ZERO
        priced_count = 0
        unpriced_count = 0

        for pos in open_positions:
            instrument = (
                db.query(Instrument)
                .filter(Instrument.id == pos.instrument_id)
                .first()
            )
            instrument_code = instrument.code if instrument else "UNKNOWN"

            asset_symbol = None
            if instrument and instrument.asset_id:
                asset = (
                    db.query(Asset)
                    .filter(Asset.id == instrument.asset_id)
                    .first()
                )
                asset_symbol = asset.symbol if asset else None

            price_dec, market_value_dec = self._resolve_price(
                db, pos, warnings,
            )

            if price_dec is not None and market_value_dec is not None:
                priced_count += 1
                total_market_value += market_value_dec
                pricing_status = "priced"
            else:
                unpriced_count += 1
                pricing_status = "unpriced"

            position_rows.append({
                "position_id": pos.id,
                "instrument_id": pos.instrument_id,
                "instrument_code": instrument_code,
                "asset_symbol": asset_symbol,
                "position_type": pos.position_type,
                "quantity": str(pos.quantity),
                "price": str(price_dec) if price_dec is not None else None,
                "market_value": str(market_value_dec) if market_value_dec is not None else None,
                "pricing_status": pricing_status,
                "allocation_weight": None,
            })

        for row in position_rows:
            if row["pricing_status"] == "priced" and total_market_value > ZERO:
                mv = Decimal(row["market_value"])
                weight = (mv / total_market_value).quantize(Decimal("0.000001"))
                row["allocation_weight"] = str(weight)

        if unpriced_count > 0:
            noun = "position" if unpriced_count == 1 else "positions"
            warnings.append(
                f"{unpriced_count} {noun} could not be priced "
                f"because no market quote link is available"
            )

        positions = [PositionSummary(**row) for row in position_rows]

        return PortfolioSummaryResponse(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            base_currency=portfolio.base_currency,
            total_market_value=str(total_market_value),
            priced_positions_count=priced_count,
            unpriced_positions_count=unpriced_count,
            warnings=warnings,
            positions=positions,
        )

    @staticmethod
    def _resolve_price(
        db: Session,
        position: PositionAtom,
        warnings: list[str],
    ) -> tuple[Decimal | None, Decimal | None]:
        """Try to resolve price via the PE instrument price bridge.
        Returns (price, market_value) or (None, None) on failure.
        """
        try:
            result = get_instrument_price(db, position.instrument_id)
        except (MarketDataLinkMissingError, QuoteNotAvailableError):
            return None, None

        price_str = result.get("price")
        if price_str is None:
            return None, None

        price_dec = Decimal(price_str)
        quantity = position.quantity if position.quantity is not None else ZERO
        market_value = (price_dec * quantity).quantize(Decimal("0.01"))
        return price_dec, market_value
