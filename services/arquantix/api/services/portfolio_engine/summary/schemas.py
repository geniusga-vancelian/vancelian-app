"""Pydantic schemas for the Portfolio Summary read model (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PositionSummary(BaseModel):
    position_id: UUID
    instrument_id: UUID
    instrument_code: str
    asset_symbol: Optional[str] = None
    position_type: str
    quantity: str
    price: Optional[str] = None
    market_value: Optional[str] = None
    allocation_weight: Optional[str] = None
    pricing_status: str  # "priced" | "unpriced"


class PortfolioSummaryResponse(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    base_currency: str
    total_market_value: str
    priced_positions_count: int
    unpriced_positions_count: int
    warnings: list[str]
    positions: list[PositionSummary]
