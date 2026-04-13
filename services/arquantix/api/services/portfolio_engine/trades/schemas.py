"""Pydantic schemas for the Trades module (Portfolio Engine — transaction layer).

No Update schema — trades are immutable.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TradeCreate(BaseModel):
    order_id: UUID
    execution_instruction_id: Optional[UUID] = None
    instrument_id: UUID
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: Decimal
    price: Decimal
    fee_amount: Decimal = Decimal("0")
    currency: str = Field(..., max_length=20)
    counterparty: Optional[str] = Field(None, max_length=100)
    external_trade_id: Optional[str] = Field(None, max_length=255)
    executed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class TradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    execution_instruction_id: Optional[UUID] = None
    instrument_id: UUID
    side: str
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    currency: str
    counterparty: Optional[str] = None
    external_trade_id: Optional[str] = None
    executed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class TradeListResponse(BaseModel):
    items: list[TradeRead]
    total: int
