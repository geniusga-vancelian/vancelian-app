"""Pydantic schemas for the Templates module (Portfolio Engine — catalog / template layer)."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..portfolios.enums import PortfolioType


# ---------------------------------------------------------------------------
# PortfolioTemplate schemas
# ---------------------------------------------------------------------------

class TemplateCreate(BaseModel):
    product_id: UUID
    template_code: str = Field(..., max_length=100)
    provisioned_portfolio_type: PortfolioType
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    base_currency: str = Field("EUR", max_length=20)
    risk_profile: Optional[str] = Field(None, max_length=50)
    strategy_definition_id: Optional[UUID] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    provisioned_portfolio_type: Optional[PortfolioType] = None
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    base_currency: Optional[str] = Field(None, max_length=20)
    risk_profile: Optional[str] = Field(None, max_length=50)
    strategy_definition_id: Optional[UUID] = None
    metadata: Optional[dict[str, Any]] = None


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    template_code: str
    provisioned_portfolio_type: str
    name: str
    description: Optional[str] = None
    base_currency: str
    risk_profile: Optional[str] = None
    strategy_definition_id: Optional[UUID] = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: list[TemplateRead]
    total: int


# ---------------------------------------------------------------------------
# TemplateAllocation schemas
# ---------------------------------------------------------------------------

class TemplateAllocationCreate(BaseModel):
    template_id: UUID
    instrument_id: UUID
    target_weight: Decimal = Field(ge=0, le=1)
    min_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    allocation_priority: int = 100

    @model_validator(mode="after")
    def _validate_weights(self) -> "TemplateAllocationCreate":
        if self.min_weight is not None and self.min_weight > self.target_weight:
            raise ValueError("min_weight must be <= target_weight")
        if self.max_weight is not None and self.max_weight < self.target_weight:
            raise ValueError("max_weight must be >= target_weight")
        if self.min_weight is not None and self.max_weight is not None and self.min_weight > self.max_weight:
            raise ValueError("min_weight must be <= max_weight")
        return self


class TemplateAllocationUpdate(BaseModel):
    target_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    min_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    allocation_priority: Optional[int] = None


class TemplateAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    instrument_id: UUID
    target_weight: Decimal
    min_weight: Optional[Decimal] = None
    max_weight: Optional[Decimal] = None
    allocation_priority: int
    created_at: datetime
    updated_at: datetime


class TemplateAllocationListResponse(BaseModel):
    items: list[TemplateAllocationRead]
    total: int
