"""SQLAlchemy model for the pe_sleeves table (Portfolio Engine — sleeve layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, String, DateTime, Index, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Sleeve(Base):
    __tablename__ = "pe_sleeves"
    __table_args__ = (
        Index("ix_pe_sleeves_portfolio_id", "portfolio_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    sleeve_type = Column(String(50), nullable=False)
    allocation_target = Column(Numeric(12, 6), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", back_populates="sleeves")
