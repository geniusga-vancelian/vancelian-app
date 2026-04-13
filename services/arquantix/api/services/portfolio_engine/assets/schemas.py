"""Pydantic schemas for the Assets module (Portfolio Engine)."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import AssetType, LiquidityProfile, RiskProfile


class AssetCreate(BaseModel):
    symbol: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    asset_type: AssetType
    valuation_source: Optional[str] = Field(None, max_length=100)
    liquidity_profile: Optional[LiquidityProfile] = None
    risk_profile: Optional[RiskProfile] = None
    supports_staking: bool = False
    supports_collateral: bool = False
    supports_borrowing: bool = False
    supports_yield: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    asset_type: Optional[AssetType] = None
    valuation_source: Optional[str] = Field(None, max_length=100)
    liquidity_profile: Optional[LiquidityProfile] = None
    risk_profile: Optional[RiskProfile] = None
    supports_staking: Optional[bool] = None
    supports_collateral: Optional[bool] = None
    supports_borrowing: Optional[bool] = None
    supports_yield: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    name: str
    asset_type: str
    valuation_source: Optional[str] = None
    liquidity_profile: Optional[str] = None
    risk_profile: Optional[str] = None
    supports_staking: bool
    supports_collateral: bool
    supports_borrowing: bool
    supports_yield: bool
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    data: list[AssetRead]
    total: int
