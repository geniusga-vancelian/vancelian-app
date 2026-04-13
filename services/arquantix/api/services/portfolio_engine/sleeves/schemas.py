"""Pydantic schemas for the Sleeves module (Portfolio Engine)."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import SleeveType


class SleeveCreate(BaseModel):
    name: str = Field(..., max_length=255)
    sleeve_type: SleeveType
    allocation_target: Optional[Decimal] = Field(None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SleeveUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    sleeve_type: Optional[SleeveType] = None
    allocation_target: Optional[Decimal] = Field(None, ge=0, le=1)
    metadata: Optional[dict[str, Any]] = None


class SleeveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    name: str
    sleeve_type: str
    allocation_target: Optional[Decimal] = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class SleeveListResponse(BaseModel):
    data: list[SleeveRead]
    total: int
