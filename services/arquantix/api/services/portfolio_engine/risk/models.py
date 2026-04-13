"""SQLAlchemy model for the pe_risk_policies table (Portfolio Engine)."""
import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Numeric, String, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class RiskPolicy(Base):
    __tablename__ = "pe_risk_policies"
    __table_args__ = (
        CheckConstraint(
            "(portfolio_id IS NOT NULL AND sleeve_id IS NULL) "
            "OR (portfolio_id IS NULL AND sleeve_id IS NOT NULL)",
            name="ck_pe_risk_policies_xor_context",
        ),
        UniqueConstraint("portfolio_id", name="uq_pe_risk_policies_portfolio"),
        UniqueConstraint("sleeve_id", name="uq_pe_risk_policies_sleeve"),
        Index("ix_pe_risk_policies_portfolio_id", "portfolio_id"),
        Index("ix_pe_risk_policies_sleeve_id", "sleeve_id"),
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
    max_asset_weight = Column(Numeric(12, 6), nullable=True)
    max_asset_class_weight = Column(Numeric(12, 6), nullable=True)
    max_position_weight = Column(Numeric(12, 6), nullable=True)
    max_leverage = Column(Numeric(12, 6), nullable=True)
    max_drawdown = Column(Numeric(12, 6), nullable=True)
    volatility_limit = Column(Numeric(12, 6), nullable=True)
    liquidity_profile_limit = Column(String(50), nullable=True)
    parameters = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", lazy="select")
    sleeve = relationship("Sleeve", lazy="select")
