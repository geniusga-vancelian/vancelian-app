"""Pydantic schemas for the Clients module (Portfolio Engine — ownership layer)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import ClientStatus, KycStatus, ReferenceCurrency


class ClientCreate(BaseModel):
    email: str = Field(..., max_length=255)
    status: ClientStatus = ClientStatus.PENDING
    kyc_status: KycStatus = KycStatus.NOT_STARTED
    reference_currency: ReferenceCurrency = ReferenceCurrency.EUR
    person_id: Optional[UUID] = None


class ClientUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    status: Optional[ClientStatus] = None
    kyc_status: Optional[KycStatus] = None
    reference_currency: Optional[ReferenceCurrency] = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    status: str
    kyc_status: str
    reference_currency: str = "EUR"
    person_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientRead]
    total: int
