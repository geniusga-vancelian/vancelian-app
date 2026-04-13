"""Pydantic schemas for the Ledger Accounts module (Portfolio Engine — accounting layer)."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import LedgerAccountType, LedgerAccountStatus


class LedgerAccountCreate(BaseModel):
    client_id: Optional[UUID] = None
    account_type: LedgerAccountType
    account_code: str = Field(..., max_length=100)
    label: str = Field(..., max_length=255)
    currency: str = Field(..., max_length=20)
    asset_id: Optional[UUID] = None
    wallet_container_id: Optional[UUID] = None
    status: LedgerAccountStatus = LedgerAccountStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)


class LedgerAccountUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=255)
    wallet_container_id: Optional[UUID] = None
    status: Optional[LedgerAccountStatus] = None
    metadata: Optional[dict[str, Any]] = None


class LedgerAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: Optional[UUID] = None
    account_type: str
    account_code: str
    label: str
    currency: str
    asset_id: Optional[UUID] = None
    wallet_container_id: Optional[UUID] = None
    balance: Decimal
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class LedgerAccountListResponse(BaseModel):
    items: list[LedgerAccountRead]
    total: int
