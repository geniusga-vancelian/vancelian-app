"""Pydantic schemas for the Rebalance Preview module (Portfolio Engine)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import PreviewStatus, TradeDirection


class PreviewItemCreate(BaseModel):
    instrument_id: UUID
    current_weight: Optional[Decimal] = None
    target_weight: Optional[Decimal] = None
    drift: Optional[Decimal] = None
    trade_required: Optional[Decimal] = None
    trade_direction: Optional[TradeDirection] = None
    estimated_trade_size: Optional[Decimal] = None


class PreviewItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    preview_id: UUID
    instrument_id: UUID
    current_weight: Optional[Decimal] = None
    target_weight: Optional[Decimal] = None
    drift: Optional[Decimal] = None
    trade_required: Optional[Decimal] = None
    trade_direction: Optional[str] = None
    estimated_trade_size: Optional[Decimal] = None


class PreviewCreate(BaseModel):
    portfolio_id: UUID
    rebalance_policy_id: Optional[UUID] = None
    drift_score: Optional[Decimal] = None
    total_turnover: Optional[Decimal] = None
    estimated_cost: Optional[Decimal] = None
    status: PreviewStatus = PreviewStatus.PENDING
    parameters: dict = Field(default_factory=dict)
    items: list[PreviewItemCreate] = Field(default_factory=list)


class PreviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    rebalance_policy_id: Optional[UUID] = None
    generated_at: datetime
    drift_score: Optional[Decimal] = None
    total_turnover: Optional[Decimal] = None
    estimated_cost: Optional[Decimal] = None
    status: str
    parameters: dict
    items: list[PreviewItemRead] = Field(default_factory=list)
    created_at: datetime


class PreviewListResponse(BaseModel):
    items: list[PreviewRead]
    total: int
