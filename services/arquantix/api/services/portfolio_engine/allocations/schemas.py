"""Pydantic schemas for the Target Allocations module (Portfolio Engine)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AllocationCreate(BaseModel):
    portfolio_id: Optional[UUID] = None
    sleeve_id: Optional[UUID] = None
    instrument_id: UUID
    target_weight: Decimal = Field(ge=0, le=1)
    min_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    rebalance_priority: int = 100

    @model_validator(mode="after")
    def _validate(self) -> "AllocationCreate":
        if (self.portfolio_id is None) == (self.sleeve_id is None):
            raise ValueError("Exactly one of portfolio_id or sleeve_id must be provided")
        if self.min_weight is not None and self.min_weight > self.target_weight:
            raise ValueError("min_weight must be <= target_weight")
        if self.max_weight is not None and self.max_weight < self.target_weight:
            raise ValueError("max_weight must be >= target_weight")
        if self.min_weight is not None and self.max_weight is not None and self.min_weight > self.max_weight:
            raise ValueError("min_weight must be <= max_weight")
        return self


class AllocationUpdate(BaseModel):
    target_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    min_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    rebalance_priority: Optional[int] = None


class AllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: Optional[UUID] = None
    sleeve_id: Optional[UUID] = None
    instrument_id: UUID
    target_weight: Decimal
    min_weight: Optional[Decimal] = None
    max_weight: Optional[Decimal] = None
    rebalance_priority: int
    created_at: datetime
    updated_at: datetime


class AllocationListResponse(BaseModel):
    items: list[AllocationRead]
    total: int
