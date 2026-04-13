"""SQLAlchemy model for the pe_product_subscriptions table
(Portfolio Engine — product subscription layer)."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class ProductSubscription(Base):
    __tablename__ = "pe_product_subscriptions"
    __table_args__ = (
        Index("ix_pe_product_subscriptions_client_id", "client_id"),
        Index("ix_pe_product_subscriptions_product_id", "product_id"),
        Index("ix_pe_product_subscriptions_status", "status"),
        Index("ix_pe_product_subscriptions_metadata", "metadata", postgresql_using="gin"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_product_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="SET NULL"),
        nullable=True,
    )
    subscription_amount = Column(Numeric(30, 10), nullable=True)
    subscription_currency = Column(String(20), nullable=False, server_default="EUR")
    status = Column(String(30), nullable=False, server_default="pending")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", lazy="select")
    product = relationship("ProductDefinition", lazy="select")
    portfolio = relationship("Portfolio", lazy="select")
