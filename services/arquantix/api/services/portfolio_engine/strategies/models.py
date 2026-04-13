"""SQLAlchemy models for pe_strategy_definitions and pe_strategy_instances
(Portfolio Engine — strategy layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class StrategyDefinition(Base):
    __tablename__ = "pe_strategy_definitions"
    __table_args__ = (
        Index("ix_pe_strategy_definitions_type", "strategy_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    parameters_schema = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class StrategyInstance(Base):
    __tablename__ = "pe_strategy_instances"
    __table_args__ = (
        Index("ix_pe_strategy_instances_portfolio_id", "portfolio_id"),
        Index("ix_pe_strategy_instances_sleeve_id", "sleeve_id"),
        Index("ix_pe_strategy_instances_definition_id", "strategy_definition_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    sleeve_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_sleeves.id", ondelete="SET NULL"),
        nullable=True,
    )
    strategy_definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_strategy_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False, server_default="active")
    priority = Column(Integer, nullable=False, server_default="100")
    parameters = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", lazy="select")
    sleeve = relationship("Sleeve", lazy="select")
    definition = relationship("StrategyDefinition", lazy="select")
