"""Pydantic schemas for the Wallet Containers module (Portfolio Engine — ledger layer)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import WalletType, WalletStatus


class WalletCreate(BaseModel):
    client_id: Optional[UUID] = None
    portfolio_id: Optional[UUID] = None
    wallet_type: WalletType
    instrument_id: Optional[UUID] = None
    custody_provider: Optional[str] = None
    blockchain_address: Optional[str] = None
    ledger_account_ref: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: WalletStatus = WalletStatus.ACTIVE
    metadata: dict = Field(default_factory=dict)


class WalletUpdate(BaseModel):
    portfolio_id: Optional[UUID] = None
    wallet_type: Optional[WalletType] = None
    instrument_id: Optional[UUID] = None
    custody_provider: Optional[str] = None
    blockchain_address: Optional[str] = None
    ledger_account_ref: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: Optional[WalletStatus] = None
    metadata: Optional[dict] = None


class WalletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: Optional[UUID] = None
    portfolio_id: Optional[UUID] = None
    wallet_type: str
    instrument_id: Optional[UUID] = None
    custody_provider: Optional[str] = None
    blockchain_address: Optional[str] = None
    ledger_account_ref: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: str
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class WalletListResponse(BaseModel):
    items: list[WalletRead]
    total: int
