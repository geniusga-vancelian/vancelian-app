"""Pydantic schemas for the Settlement module (Portfolio Engine — settlement layer).

No arbitrary Update schema — status transitions are handled through dedicated service methods.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import SettlementType, SettlementStatus


class SettlementCreate(BaseModel):
    order_id: Optional[UUID] = None
    trade_id: Optional[UUID] = None
    settlement_group_id: Optional[UUID] = None
    settlement_type: SettlementType
    from_account_id: UUID
    to_account_id: UUID
    asset_id: UUID
    amount: Decimal = Field(..., gt=0)
    scheduled_at: Optional[datetime] = None
    external_reference: Optional[str] = Field(None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SettlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: Optional[UUID] = None
    trade_id: Optional[UUID] = None
    settlement_group_id: Optional[UUID] = None
    settlement_type: str
    from_account_id: UUID
    to_account_id: UUID
    asset_id: UUID
    amount: Decimal
    status: str
    scheduled_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    external_reference: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class SettlementListResponse(BaseModel):
    items: list[SettlementRead]
    total: int


class SettlementLeg(BaseModel):
    """Describes one leg of a trade-related settlement group."""
    settlement_type: SettlementType
    from_account_id: UUID
    to_account_id: UUID
    asset_id: UUID
    amount: Decimal = Field(..., gt=0)
    scheduled_at: Optional[datetime] = None
