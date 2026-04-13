"""Pydantic schemas for the Risk Policies module (Portfolio Engine)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskPolicyCreate(BaseModel):
    portfolio_id: Optional[UUID] = None
    sleeve_id: Optional[UUID] = None
    max_asset_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_asset_class_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_position_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_leverage: Optional[Decimal] = Field(default=None, ge=0)
    max_drawdown: Optional[Decimal] = Field(default=None, ge=0, le=1)
    volatility_limit: Optional[Decimal] = Field(default=None, ge=0)
    liquidity_profile_limit: Optional[str] = None
    parameters: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_xor(self) -> "RiskPolicyCreate":
        if (self.portfolio_id is None) == (self.sleeve_id is None):
            raise ValueError("Exactly one of portfolio_id or sleeve_id must be provided")
        return self


class RiskPolicyUpdate(BaseModel):
    max_asset_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_asset_class_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_position_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_leverage: Optional[Decimal] = Field(default=None, ge=0)
    max_drawdown: Optional[Decimal] = Field(default=None, ge=0, le=1)
    volatility_limit: Optional[Decimal] = Field(default=None, ge=0)
    liquidity_profile_limit: Optional[str] = None
    parameters: Optional[dict] = None


class RiskPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: Optional[UUID] = None
    sleeve_id: Optional[UUID] = None
    max_asset_weight: Optional[Decimal] = None
    max_asset_class_weight: Optional[Decimal] = None
    max_position_weight: Optional[Decimal] = None
    max_leverage: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    volatility_limit: Optional[Decimal] = None
    liquidity_profile_limit: Optional[str] = None
    parameters: dict
    created_at: datetime
    updated_at: datetime
