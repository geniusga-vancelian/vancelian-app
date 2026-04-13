"""Pydantic schemas for the Ledger Entries module (Portfolio Engine — accounting layer).

No Update schema — ledger entries are append-only.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import EntryType, ReferenceType


class LedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    entry_type: str
    amount: Decimal
    currency: str
    asset_id: Optional[UUID] = None
    reference_type: str
    reference_id: Optional[UUID] = None
    counterpart_entry_id: Optional[UUID] = None
    description: Optional[str] = None
    effective_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class LedgerEntryListResponse(BaseModel):
    items: list[LedgerEntryRead]
    total: int
