"""Pydantic schemas for the Execution module (Portfolio Engine — execution layer).

No arbitrary Update schema — status transitions and fill updates are handled through
dedicated service methods.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import ExecutionType, ExecutionVenue


class ExecutionCreate(BaseModel):
    order_id: UUID
    parent_execution_id: Optional[UUID] = None
    venue: ExecutionVenue
    execution_type: ExecutionType
    instrument_id: Optional[UUID] = None
    side: Optional[str] = Field(None, pattern="^(buy|sell)$")
    quantity: Optional[Decimal] = Field(None, gt=0)
    amount: Optional[Decimal] = Field(None, gt=0)
    price_limit: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=20)
    requested_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    parent_execution_id: Optional[UUID] = None
    venue: str
    execution_type: str
    instrument_id: Optional[UUID] = None
    side: Optional[str] = None
    quantity: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    price_limit: Optional[Decimal] = None
    currency: Optional[str] = None
    status: str
    venue_order_id: Optional[str] = None
    filled_quantity: Optional[Decimal] = None
    average_fill_price: Optional[Decimal] = None
    requested_at: datetime
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    response_payload: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class ExecutionListResponse(BaseModel):
    items: list[ExecutionRead]
    total: int


class FillReport(BaseModel):
    """Data describing a single fill event from a venue."""
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(..., max_length=20)
    counterparty: Optional[str] = Field(None, max_length=100)
    external_trade_id: Optional[str] = Field(None, max_length=255)
    executed_at: datetime
