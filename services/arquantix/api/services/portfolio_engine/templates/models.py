"""SQLAlchemy models for pe_portfolio_templates and pe_template_allocations
(Portfolio Engine — catalog / template layer)."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class PortfolioTemplate(Base):
    __tablename__ = "pe_portfolio_templates"
    __table_args__ = (
        Index("ix_pe_portfolio_templates_product_id", "product_id"),
        Index("ix_pe_portfolio_templates_metadata", "metadata", postgresql_using="gin"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_product_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_code = Column(String(100), unique=True, nullable=False, index=True)
    provisioned_portfolio_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    base_currency = Column(String(20), nullable=False, server_default="EUR")
    risk_profile = Column(String(50), nullable=True)
    strategy_definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_strategy_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    product = relationship("ProductDefinition", lazy="select")
    strategy_definition = relationship("StrategyDefinition", lazy="select")
    allocations = relationship("TemplateAllocation", back_populates="template", lazy="select")


class TemplateAllocation(Base):
    __tablename__ = "pe_template_allocations"
    __table_args__ = (
        UniqueConstraint("template_id", "instrument_id", name="uq_pe_template_allocations_template_instrument"),
        Index("ix_pe_template_allocations_template_id", "template_id"),
        Index("ix_pe_template_allocations_instrument_id", "instrument_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolio_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_weight = Column(Numeric(12, 6), nullable=False)
    min_weight = Column(Numeric(12, 6), nullable=True)
    max_weight = Column(Numeric(12, 6), nullable=True)
    allocation_priority = Column(Integer, nullable=False, server_default="100")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    template = relationship("PortfolioTemplate", back_populates="allocations", lazy="select")
    instrument = relationship("Instrument", lazy="select")
