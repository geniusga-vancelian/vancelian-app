"""SQLAlchemy models for the pe_rebalance_previews / pe_rebalance_preview_items tables."""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class RebalancePreview(Base):
    __tablename__ = "pe_rebalance_previews"
    __table_args__ = (
        Index("ix_pe_rebalance_previews_portfolio_id", "portfolio_id"),
        Index("ix_pe_rebalance_previews_generated_at", "generated_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    rebalance_policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_rebalance_policies.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    drift_score = Column(Numeric(12, 6), nullable=True)
    total_turnover = Column(Numeric(12, 6), nullable=True)
    estimated_cost = Column(Numeric(30, 10), nullable=True)
    status = Column(String(30), nullable=False, server_default="pending")
    parameters = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    portfolio = relationship("Portfolio", lazy="select")
    rebalance_policy = relationship("RebalancePolicy", lazy="select")
    items = relationship("RebalancePreviewItem", back_populates="preview", cascade="all, delete-orphan", lazy="select")


class RebalancePreviewItem(Base):
    __tablename__ = "pe_rebalance_preview_items"
    __table_args__ = (
        Index("ix_pe_rebalance_preview_items_preview_id", "preview_id"),
        Index("ix_pe_rebalance_preview_items_instrument_id", "instrument_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    preview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_rebalance_previews.id", ondelete="CASCADE"),
        nullable=False,
    )
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_weight = Column(Numeric(12, 6), nullable=True)
    target_weight = Column(Numeric(12, 6), nullable=True)
    drift = Column(Numeric(12, 6), nullable=True)
    trade_required = Column(Numeric(30, 10), nullable=True)
    trade_direction = Column(String(10), nullable=True)
    estimated_trade_size = Column(Numeric(30, 10), nullable=True)

    preview = relationship("RebalancePreview", back_populates="items")
    instrument = relationship("Instrument", lazy="select")
