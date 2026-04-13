"""Pydantic schemas for the Position Atoms module (Portfolio Engine — position layer)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import PositionType, PositionStatus, LockupStatus


class PositionCreate(BaseModel):
    portfolio_id: UUID
    sleeve_id: Optional[UUID] = None
    wallet_id: Optional[UUID] = None
    instrument_id: UUID
    strategy_instance_id: Optional[UUID] = None
    parent_position_id: Optional[UUID] = None
    position_type: PositionType
    status: PositionStatus = PositionStatus.OPEN
    quantity: Decimal = Decimal("0")
    available_quantity: Decimal = Decimal("0")
    locked_quantity: Decimal = Decimal("0")
    market_value: Optional[Decimal] = None
    cost_basis: Optional[Decimal] = None
    average_entry_price: Optional[Decimal] = None
    accrued_income: Decimal = Decimal("0")
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Decimal = Decimal("0")
    lockup_status: Optional[LockupStatus] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class PositionUpdate(BaseModel):
    sleeve_id: Optional[UUID] = None
    wallet_id: Optional[UUID] = None
    strategy_instance_id: Optional[UUID] = None
    parent_position_id: Optional[UUID] = None
    position_type: Optional[PositionType] = None
    status: Optional[PositionStatus] = None
    quantity: Optional[Decimal] = None
    available_quantity: Optional[Decimal] = None
    locked_quantity: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    cost_basis: Optional[Decimal] = None
    average_entry_price: Optional[Decimal] = None
    accrued_income: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    lockup_status: Optional[LockupStatus] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    sleeve_id: Optional[UUID] = None
    wallet_id: Optional[UUID] = None
    instrument_id: UUID
    strategy_instance_id: Optional[UUID] = None
    parent_position_id: Optional[UUID] = None
    position_type: str
    status: str
    quantity: Decimal
    available_quantity: Decimal
    locked_quantity: Decimal
    market_value: Optional[Decimal] = None
    cost_basis: Optional[Decimal] = None
    average_entry_price: Optional[Decimal] = None
    accrued_income: Decimal
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Decimal
    lockup_status: Optional[str] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class PositionListResponse(BaseModel):
    items: list[PositionRead]
    total: int
