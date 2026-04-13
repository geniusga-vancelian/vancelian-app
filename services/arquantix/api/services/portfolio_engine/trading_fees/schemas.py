"""Pydantic schemas for TradingFeeConfig."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TradingFeeConfigCreate(BaseModel):
    scope_type: str = Field(..., max_length=30)
    scope_id: Optional[UUID] = None
    fee_type: str = Field(default="trading", max_length=30)
    fee_rate: Decimal = Field(..., ge=0, le=1)
    min_fee: Optional[Decimal] = None
    max_fee: Optional[Decimal] = None
    status: str = Field(default="active", max_length=20)
    valid_from: datetime
    valid_to: Optional[datetime] = None
    metadata: Optional[dict] = Field(default_factory=dict)


class TradingFeeConfigUpdate(BaseModel):
    scope_type: Optional[str] = Field(default=None, max_length=30)
    scope_id: Optional[UUID] = None
    fee_type: Optional[str] = Field(default=None, max_length=30)
    fee_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    min_fee: Optional[Decimal] = None
    max_fee: Optional[Decimal] = None
    status: Optional[str] = Field(default=None, max_length=20)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    metadata: Optional[dict] = None


class TradingFeeConfigRead(BaseModel):
    id: UUID
    scope_type: str
    scope_id: Optional[UUID]
    fee_type: str
    fee_rate: Decimal
    min_fee: Optional[Decimal]
    max_fee: Optional[Decimal]
    status: str
    valid_from: datetime
    valid_to: Optional[datetime]
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TradingFeeConfigListResponse(BaseModel):
    items: list[TradingFeeConfigRead]
    total: int


class FeeCalculationResult(BaseModel):
    gross_amount: Decimal
    fee_rate: Decimal
    fee_amount: Decimal
    config_id: Optional[UUID] = None
