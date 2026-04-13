"""Pydantic schemas for the Drift Detection & Rebalance Engine (Phase 6)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DriftItemResult(BaseModel):
    instrument_id: UUID
    instrument_code: str
    asset_symbol: Optional[str] = None
    target_weight: str
    current_weight: str
    drift: str
    exceeds_threshold: bool
    is_unallocated: bool


class DriftReport(BaseModel):
    portfolio_id: UUID
    nav: str
    threshold: str
    max_absolute_drift: str
    drift_score: str
    needs_rebalance: bool
    priced_positions_count: int
    unpriced_excluded_count: int
    warnings: list[str]
    items: list[DriftItemResult]


class RebalanceTradeItem(BaseModel):
    instrument_id: UUID
    instrument_code: str
    asset_symbol: Optional[str] = None
    target_weight: str
    current_weight: str
    drift: str
    action: str
    trade_value: Optional[str] = None
    trade_quantity: Optional[str] = None
    price: Optional[str] = None


class RebalancePreviewResponse(BaseModel):
    portfolio_id: UUID
    nav: str
    threshold: str
    needs_rebalance: bool
    drift_score: str
    warnings: list[str]
    trades: list[RebalanceTradeItem]
