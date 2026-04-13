"""SQLAlchemy models for valuation snapshot tables (Phase 5).

Both tables are append-only: no UPDATE, no DELETE.
"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class PositionValuation(Base):
    __tablename__ = "pe_position_valuations"
    __table_args__ = (
        Index("ix_pe_position_valuations_position_id", "position_id"),
        Index("ix_pe_position_valuations_portfolio_id", "portfolio_id"),
        Index("ix_pe_position_valuations_valuation_ts", "valuation_timestamp"),
        Index("ix_pe_position_valuations_portfolio_ts", "portfolio_id", "valuation_timestamp"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    position_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_position_atoms.id", ondelete="CASCADE"),
        nullable=False,
    )
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity = Column(Numeric(30, 10), nullable=False)
    price = Column(Numeric(30, 10), nullable=True)
    market_value = Column(Numeric(30, 10), nullable=True)
    average_entry_price = Column(Numeric(30, 10), nullable=True)
    unrealized_pnl = Column(Numeric(30, 10), nullable=True)
    realized_pnl = Column(Numeric(30, 10), nullable=False, server_default="0")
    pricing_status = Column(String(20), nullable=False)
    valuation_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PortfolioValuation(Base):
    __tablename__ = "pe_portfolio_valuations"
    __table_args__ = (
        Index("ix_pe_portfolio_valuations_portfolio_id", "portfolio_id"),
        Index("ix_pe_portfolio_valuations_valuation_ts", "valuation_timestamp"),
        Index("ix_pe_portfolio_valuations_portfolio_ts", "portfolio_id", "valuation_timestamp"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    nav = Column(Numeric(30, 10), nullable=False)
    total_realized_pnl = Column(Numeric(30, 10), nullable=False)
    total_unrealized_pnl = Column(Numeric(30, 10), nullable=False)
    total_pnl = Column(Numeric(30, 10), nullable=False)
    priced_positions_count = Column(Integer, nullable=False)
    unpriced_positions_count = Column(Integer, nullable=False)
    valuation_source = Column(String(30), nullable=False)
    valuation_timestamp = Column(DateTime(timezone=True), nullable=False)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
