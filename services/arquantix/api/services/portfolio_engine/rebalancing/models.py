"""SQLAlchemy model for the pe_rebalance_policies table (Portfolio Engine)."""
import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Numeric, String, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class RebalancePolicy(Base):
    __tablename__ = "pe_rebalance_policies"
    __table_args__ = (
        CheckConstraint(
            "(portfolio_id IS NOT NULL AND sleeve_id IS NULL) "
            "OR (portfolio_id IS NULL AND sleeve_id IS NOT NULL)",
            name="ck_pe_rebalance_policies_xor_context",
        ),
        UniqueConstraint("portfolio_id", name="uq_pe_rebalance_policies_portfolio"),
        UniqueConstraint("sleeve_id", name="uq_pe_rebalance_policies_sleeve"),
        Index("ix_pe_rebalance_policies_portfolio_id", "portfolio_id"),
        Index("ix_pe_rebalance_policies_sleeve_id", "sleeve_id"),
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
    method = Column(String(50), nullable=False)
    frequency = Column(String(50), nullable=True)
    drift_threshold = Column(Numeric(12, 6), nullable=True)
    min_trade_size = Column(Numeric(30, 10), nullable=True)
    transaction_cost_model = Column(String(50), nullable=True)
    lockup_aware = Column(Boolean, nullable=False, server_default="true")
    cash_flow_priority = Column(Boolean, nullable=False, server_default="true")
    parameters = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", lazy="select")
    sleeve = relationship("Sleeve", lazy="select")
