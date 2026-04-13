"""Pydantic schemas for P2P Lending API."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateLoanRequest(BaseModel):
    lender_client_id: UUID
    borrower_client_id: UUID
    asset: str = Field(..., min_length=1, max_length=20)
    principal: Decimal = Field(..., gt=0)
    interest_rate_bps: int = Field(0, ge=0, le=5000)
    platform_fee_bps: int = Field(0, ge=0, le=2000)
    duration_days: int = Field(30, ge=1, le=365)


class AcceptLoanRequest(BaseModel):
    borrower_client_id: UUID


class RepayLoanRequest(BaseModel):
    borrower_client_id: UUID


class LoanResponse(BaseModel):
    id: UUID
    lender_client_id: UUID
    borrower_client_id: UUID
    asset: str
    principal: Decimal
    interest_rate_bps: int
    platform_fee_bps: int
    duration_days: int
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    repaid_at: Optional[datetime] = None
    status: str
    lender_position_atom_id: Optional[UUID] = None
    borrower_position_atom_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoanDetailResponse(BaseModel):
    """Enriched loan response for Flutter UI."""
    id: UUID
    role: str
    counterparty_id: UUID
    counterparty_email: Optional[str] = None
    asset: str
    principal: Decimal
    market_value_eur: Optional[float] = None
    status: str
    start_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LendingSummaryResponse(BaseModel):
    """Dashboard summary for a client's lending activity."""
    client_id: UUID
    total_lent_count: int = 0
    total_borrowed_count: int = 0
    total_lent_value_eur: float = 0.0
    total_borrowed_value_eur: float = 0.0
    active_loans_as_lender: list[LoanDetailResponse] = []
    active_loans_as_borrower: list[LoanDetailResponse] = []
    pending_offers_received: list[LoanDetailResponse] = []


class LoanRepaymentSummary(BaseModel):
    loan_id: UUID
    principal: Decimal
    interest: Decimal
    platform_fee: Decimal
    lender_receives: Decimal
    borrower_pays: Decimal
    elapsed_days: int
