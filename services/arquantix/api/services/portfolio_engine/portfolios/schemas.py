"""Pydantic schemas for the Portfolios module (Portfolio Engine)."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import PortfolioStatus, PortfolioType
from ..assets.enums import RiskProfile


class PortfolioCreate(BaseModel):
    client_id: UUID
    parent_portfolio_id: Optional[UUID] = None
    origin_product_id: Optional[UUID] = None
    portfolio_type: PortfolioType
    name: str = Field(..., max_length=255)
    base_currency: str = Field("EUR", max_length=20)
    risk_profile: Optional[RiskProfile] = None
    status: PortfolioStatus = PortfolioStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    origin_product_id: Optional[UUID] = None
    portfolio_type: Optional[PortfolioType] = None
    base_currency: Optional[str] = Field(None, max_length=20)
    risk_profile: Optional[RiskProfile] = None
    status: Optional[PortfolioStatus] = None
    metadata: Optional[dict[str, Any]] = None


class PortfolioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    parent_portfolio_id: Optional[UUID] = None
    origin_product_id: Optional[UUID] = None
    portfolio_type: str
    name: str
    base_currency: str
    risk_profile: Optional[str] = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class PortfolioListResponse(BaseModel):
    data: list[PortfolioRead]
    total: int
