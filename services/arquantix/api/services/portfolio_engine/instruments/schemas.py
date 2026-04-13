"""Pydantic schemas for the Instruments module (Portfolio Engine)."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import InstrumentType, ValuationMethod
from ..assets.enums import LiquidityProfile


class InstrumentCreate(BaseModel):
    asset_id: UUID
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    instrument_type: InstrumentType
    liquidity_profile: Optional[LiquidityProfile] = None
    lockup_period_days: Optional[int] = Field(None, ge=0)
    valuation_method: Optional[ValuationMethod] = None
    yield_source: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InstrumentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    instrument_type: Optional[InstrumentType] = None
    liquidity_profile: Optional[LiquidityProfile] = None
    lockup_period_days: Optional[int] = Field(None, ge=0)
    valuation_method: Optional[ValuationMethod] = None
    yield_source: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=100)
    metadata: Optional[dict[str, Any]] = None


class InstrumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    code: str
    name: str
    instrument_type: str
    liquidity_profile: Optional[str] = None
    lockup_period_days: Optional[int] = None
    valuation_method: Optional[str] = None
    yield_source: Optional[str] = None
    provider: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class InstrumentListResponse(BaseModel):
    data: list[InstrumentRead]
    total: int


class InstrumentPriceRead(BaseModel):
    instrument_id: str
    instrument_code: str
    asset_symbol: Optional[str] = None
    market_data_instrument_id: int
    provider: str
    provider_symbol: Optional[str] = None
    price: Optional[str] = None
    bid_price: Optional[str] = None
    ask_price: Optional[str] = None
    volume_24h: Optional[str] = None
    quote_time: Optional[str] = None
    updated_at: Optional[str] = None
