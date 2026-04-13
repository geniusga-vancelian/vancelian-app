"""SQLAlchemy models for Pool-based P2P Lending (Phase 2A.6bis).

Tables:
  - lending_pools:              one pool per asset
  - pool_supply_commitments:    lender liquidity reservations
  - pool_borrow_positions:      borrower active borrows
  - pool_allocations:           audit trail linking supply → borrow
"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class LendingPool(Base):
    __tablename__ = "lending_pools"
    __table_args__ = (
        Index("ix_lending_pools_asset", "asset"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    asset = Column(String(20), nullable=False)
    total_committed = Column(Numeric(30, 10), nullable=False, server_default="0")
    total_borrowed = Column(Numeric(30, 10), nullable=False, server_default="0")
    utilization_rate = Column(Numeric(10, 4), nullable=False, server_default="0")
    borrow_rate_bps = Column(Numeric(10, 2), nullable=False, server_default="500")
    supply_rate_bps = Column(Numeric(10, 2), nullable=False, server_default="300")
    status = Column(String(30), nullable=False, server_default="active")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PoolSupplyCommitment(Base):
    __tablename__ = "pool_supply_commitments"
    __table_args__ = (
        Index("ix_pool_supply_commitments_pool_id", "pool_id"),
        Index("ix_pool_supply_commitments_client_id", "client_id"),
        Index("ix_pool_supply_commitments_status", "status"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    pool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.lending_pools.id", ondelete="RESTRICT"),
        nullable=False,
    )
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset = Column(String(20), nullable=False)
    amount = Column(Numeric(30, 10), nullable=False)
    reserved_amount = Column(Numeric(30, 10), nullable=False, server_default="0")
    available_amount = Column(Numeric(30, 10), nullable=False, server_default="0")
    status = Column(String(30), nullable=False, server_default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PoolBorrowPosition(Base):
    __tablename__ = "pool_borrow_positions"
    __table_args__ = (
        Index("ix_pool_borrow_positions_pool_id", "pool_id"),
        Index("ix_pool_borrow_positions_client_id", "client_id"),
        Index("ix_pool_borrow_positions_status", "status"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    pool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.lending_pools.id", ondelete="RESTRICT"),
        nullable=False,
    )
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset = Column(String(20), nullable=False)
    borrowed_amount = Column(Numeric(30, 10), nullable=False)
    status = Column(String(30), nullable=False, server_default="active")
    borrowing_position_atom_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PoolAllocation(Base):
    __tablename__ = "pool_allocations"
    __table_args__ = (
        Index("ix_pool_allocations_supply_id", "supply_commitment_id"),
        Index("ix_pool_allocations_borrow_id", "borrow_position_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    supply_commitment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pool_supply_commitments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    borrow_position_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pool_borrow_positions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount = Column(Numeric(30, 10), nullable=False)
    lending_position_atom_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
