"""Pydantic schemas for the Valuation & Performance Engine (Phase 5)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PositionValuationResult(BaseModel):
    position_id: UUID
    instrument_id: UUID
    instrument_code: str
    asset_symbol: Optional[str] = None
    position_type: str
    quantity: str
    average_entry_price: Optional[str] = None
    price: Optional[str] = None
    market_value: Optional[str] = None
    unrealized_pnl: Optional[str] = None
    realized_pnl: str
    allocation_weight: Optional[str] = None
    pricing_status: str
    valuation_timestamp: datetime


class PortfolioValuationResponse(BaseModel):
    portfolio_id: UUID
    portfolio_name: str
    base_currency: str
    nav: str
    total_realized_pnl: str
    total_unrealized_pnl: str
    total_pnl: str
    priced_positions_count: int
    unpriced_positions_count: int
    warnings: list[str]
    positions: list[PositionValuationResult]
    valuation_timestamp: datetime


class PositionValuationSnapshotRead(BaseModel):
    id: UUID
    position_id: UUID
    portfolio_id: UUID
    instrument_id: UUID
    quantity: str
    price: Optional[str] = None
    market_value: Optional[str] = None
    average_entry_price: Optional[str] = None
    unrealized_pnl: Optional[str] = None
    realized_pnl: str
    pricing_status: str
    valuation_timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioValuationSnapshotRead(BaseModel):
    id: UUID
    portfolio_id: UUID
    nav: str
    total_realized_pnl: str
    total_unrealized_pnl: str
    total_pnl: str
    priced_positions_count: int
    unpriced_positions_count: int
    valuation_source: str
    valuation_timestamp: datetime
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioValuationHistoryResponse(BaseModel):
    items: list[PortfolioValuationSnapshotRead]
    total: int
