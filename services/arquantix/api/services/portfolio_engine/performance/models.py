"""SQLAlchemy model for pe_portfolio_return_series (Phase 9 — Performance Engine).

Append-only table. No UPDATE / DELETE paths.
"""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class PortfolioReturnSeries(Base):
    __tablename__ = "pe_portfolio_return_series"
    __table_args__ = (
        Index("ix_pe_portfolio_return_series_portfolio_id", "portfolio_id"),
        Index("ix_pe_portfolio_return_series_timestamp", "timestamp"),
        Index("ix_pe_portfolio_return_series_pf_ts", "portfolio_id", "timestamp"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    valuation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolio_valuations.id", ondelete="SET NULL"),
        nullable=True,
    )
    timestamp = Column(DateTime(timezone=True), nullable=False)
    nav = Column(Numeric(30, 10), nullable=False)
    period_return = Column(Numeric(20, 10), nullable=True)
    cumulative_return = Column(Numeric(20, 10), nullable=True)
    drawdown = Column(Numeric(20, 10), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
