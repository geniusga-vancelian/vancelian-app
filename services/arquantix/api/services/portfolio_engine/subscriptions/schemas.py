"""Pydantic schemas for the Subscriptions module
(Portfolio Engine — product subscription layer)."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import SubscriptionStatus


class SubscriptionCreate(BaseModel):
    client_id: UUID
    product_id: UUID
    portfolio_id: Optional[UUID] = None
    subscription_amount: Optional[Decimal] = Field(default=None, ge=0)
    subscription_currency: str = Field("EUR", max_length=20)
    status: SubscriptionStatus = SubscriptionStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubscriptionUpdate(BaseModel):
    portfolio_id: Optional[UUID] = None
    subscription_amount: Optional[Decimal] = Field(default=None, ge=0)
    subscription_currency: Optional[str] = Field(None, max_length=20)
    status: Optional[SubscriptionStatus] = None
    metadata: Optional[dict[str, Any]] = None


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    product_id: UUID
    portfolio_id: Optional[UUID] = None
    subscription_amount: Optional[Decimal] = None
    subscription_currency: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionRead]
    total: int


class ProvisionRequest(BaseModel):
    template_id: UUID
