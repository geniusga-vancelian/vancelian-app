"""SQLAlchemy models for P2P internal lending (Phase 2A)."""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        Index("ix_loans_lender_client_id", "lender_client_id"),
        Index("ix_loans_borrower_client_id", "borrower_client_id"),
        Index("ix_loans_status", "status"),
        Index("ix_loans_asset", "asset"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    lender_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    borrower_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    asset = Column(String(20), nullable=False)
    principal = Column(Numeric(30, 10), nullable=False)

    interest_rate_bps = Column(Integer, nullable=False, server_default="0")
    platform_fee_bps = Column(Integer, nullable=False, server_default="0")

    duration_days = Column(Integer, nullable=False)

    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    repaid_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(30), nullable=False, server_default="pending")

    lender_position_atom_id = Column(UUID(as_uuid=True), nullable=True)
    borrower_position_atom_id = Column(UUID(as_uuid=True), nullable=True)

    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LoanInterestAccrual(Base):
    __tablename__ = "loan_interest_accruals"
    __table_args__ = (
        Index("ix_loan_interest_accruals_loan_id", "loan_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    loan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.loans.id", ondelete="CASCADE"),
        nullable=False,
    )
    accrued_amount = Column(Numeric(30, 10), nullable=False, server_default="0")
    last_accrual_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
