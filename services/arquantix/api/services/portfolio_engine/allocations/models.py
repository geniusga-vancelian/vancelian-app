"""SQLAlchemy model for the pe_target_allocations table (Portfolio Engine)."""
import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class TargetAllocation(Base):
    __tablename__ = "pe_target_allocations"
    __table_args__ = (
        CheckConstraint(
            "(portfolio_id IS NOT NULL AND sleeve_id IS NULL) "
            "OR (portfolio_id IS NULL AND sleeve_id IS NOT NULL)",
            name="ck_pe_target_allocations_xor_context",
        ),
        UniqueConstraint("portfolio_id", "instrument_id", name="uq_pe_target_allocations_portfolio_instrument"),
        UniqueConstraint("sleeve_id", "instrument_id", name="uq_pe_target_allocations_sleeve_instrument"),
        Index("ix_pe_target_allocations_portfolio_id", "portfolio_id"),
        Index("ix_pe_target_allocations_sleeve_id", "sleeve_id"),
        Index("ix_pe_target_allocations_instrument_id", "instrument_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=True,
    )
    sleeve_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_sleeves.id", ondelete="CASCADE"),
        nullable=True,
    )
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_weight = Column(Numeric(12, 6), nullable=False)
    min_weight = Column(Numeric(12, 6), nullable=True)
    max_weight = Column(Numeric(12, 6), nullable=True)
    rebalance_priority = Column(Integer, nullable=False, server_default="100")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", lazy="select")
    sleeve = relationship("Sleeve", lazy="select")
    instrument = relationship("Instrument", lazy="select")
