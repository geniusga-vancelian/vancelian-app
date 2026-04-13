"""Pydantic schemas for the Orders module (Portfolio Engine — transaction layer)."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import OrderType, OrderSide, OrderStatus


class OrderCreate(BaseModel):
    client_id: UUID
    portfolio_id: UUID
    instrument_id: Optional[UUID] = None
    order_type: OrderType
    side: Optional[OrderSide] = None
    quantity: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=20)
    price_limit: Optional[Decimal] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    portfolio_id: UUID
    instrument_id: Optional[UUID] = None
    order_type: str
    side: Optional[str] = None
    quantity: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    price_limit: Optional[Decimal] = None
    status: str
    rejection_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderRead]
    total: int
