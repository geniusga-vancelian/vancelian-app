"""Pydantic schemas for the Rebalance Policies module (Portfolio Engine)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import RebalanceMethod, RebalanceFrequency


class RebalancePolicyCreate(BaseModel):
    portfolio_id: Optional[UUID] = None
    sleeve_id: Optional[UUID] = None
    method: RebalanceMethod
    frequency: Optional[RebalanceFrequency] = None
    drift_threshold: Optional[Decimal] = Field(default=None, ge=0)
    min_trade_size: Optional[Decimal] = Field(default=None, ge=0)
    transaction_cost_model: Optional[str] = None
    lockup_aware: bool = True
    cash_flow_priority: bool = True
    parameters: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_xor(self) -> "RebalancePolicyCreate":
        if (self.portfolio_id is None) == (self.sleeve_id is None):
            raise ValueError("Exactly one of portfolio_id or sleeve_id must be provided")
        return self


class RebalancePolicyUpdate(BaseModel):
    method: Optional[RebalanceMethod] = None
    frequency: Optional[RebalanceFrequency] = None
    drift_threshold: Optional[Decimal] = Field(default=None, ge=0)
    min_trade_size: Optional[Decimal] = Field(default=None, ge=0)
    transaction_cost_model: Optional[str] = None
    lockup_aware: Optional[bool] = None
    cash_flow_priority: Optional[bool] = None
    parameters: Optional[dict] = None


class RebalancePolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: Optional[UUID] = None
    sleeve_id: Optional[UUID] = None
    method: str
    frequency: Optional[str] = None
    drift_threshold: Optional[Decimal] = None
    min_trade_size: Optional[Decimal] = None
    transaction_cost_model: Optional[str] = None
    lockup_aware: bool
    cash_flow_priority: bool
    parameters: dict
    created_at: datetime
    updated_at: datetime


class RebalancePolicyListResponse(BaseModel):
    items: list[RebalancePolicyRead]
    total: int
