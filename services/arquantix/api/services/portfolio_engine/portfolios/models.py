"""SQLAlchemy model for the pe_portfolios table (Portfolio Engine — portfolio layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, String, DateTime, Index, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Portfolio(Base):
    __tablename__ = "pe_portfolios"
    __table_args__ = (
        Index("ix_pe_portfolios_client_id", "client_id"),
        Index("ix_pe_portfolios_portfolio_type", "portfolio_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    # TODO: add FK to pe_clients.id when the clients module is implemented.
    client_id = Column(UUID(as_uuid=True), nullable=False)
    parent_portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="SET NULL"),
        nullable=True,
    )
    origin_product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_product_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    portfolio_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    base_currency = Column(String(20), nullable=False, server_default="EUR")
    risk_profile = Column(String(50), nullable=True)
    status = Column(String(30), nullable=False, server_default="active")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    parent = relationship("Portfolio", remote_side=[id], lazy="select")
    origin_product = relationship("ProductDefinition", lazy="select")
    sleeves = relationship("Sleeve", back_populates="portfolio", lazy="select")
