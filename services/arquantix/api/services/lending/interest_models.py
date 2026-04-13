"""SQLAlchemy models for Pool Interest Engine (Phase 2A.7).

Tables:
  - pool_interest_snapshots:     daily aggregate snapshot per pool
  - lender_interest_accruals:    daily interest earned per lender
  - borrower_interest_accruals:  daily interest due per borrower
"""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class PoolInterestSnapshot(Base):
    __tablename__ = "pool_interest_snapshots"
    __table_args__ = (
        Index("ix_pool_interest_snapshots_pool_date", "pool_id", "date", unique=True),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    pool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.lending_pools.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(Date, nullable=False)
    total_borrowed = Column(Numeric(30, 10), nullable=False)
    borrow_rate_bps = Column(Numeric(10, 2), nullable=False)
    supply_rate_bps = Column(Numeric(10, 2), nullable=False)
    interest_generated = Column(Numeric(30, 10), nullable=False, server_default="0")
    interest_to_lenders = Column(Numeric(30, 10), nullable=False, server_default="0")
    platform_fee = Column(Numeric(30, 10), nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LenderInterestAccrual(Base):
    __tablename__ = "lender_interest_accruals"
    __table_args__ = (
        Index("ix_lender_interest_accruals_client_pool_date", "client_id", "pool_id", "date", unique=True),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.lending_pools.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(Date, nullable=False)
    allocated_amount = Column(Numeric(30, 10), nullable=False)
    interest_earned = Column(Numeric(30, 10), nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BorrowerInterestAccrual(Base):
    __tablename__ = "borrower_interest_accruals"
    __table_args__ = (
        Index("ix_borrower_interest_accruals_client_pool_date", "client_id", "pool_id", "date", unique=True),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.lending_pools.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(Date, nullable=False)
    borrowed_amount = Column(Numeric(30, 10), nullable=False)
    interest_due = Column(Numeric(30, 10), nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
