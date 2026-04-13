"""SQLAlchemy model for the pe_orders table (Portfolio Engine — transaction layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class Order(Base):
    __tablename__ = "pe_orders"
    __table_args__ = (
        Index("ix_pe_orders_client_id", "client_id"),
        Index("ix_pe_orders_portfolio_id", "portfolio_id"),
        Index("ix_pe_orders_instrument_id", "instrument_id"),
        Index("ix_pe_orders_order_type", "order_type"),
        Index("ix_pe_orders_status", "status"),
        Index("ix_pe_orders_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="SET NULL"),
        nullable=True,
    )
    order_type = Column(String(50), nullable=False)
    side = Column(String(10), nullable=True)
    quantity = Column(Numeric(30, 10), nullable=True)
    amount = Column(Numeric(30, 10), nullable=True)
    currency = Column(String(20), nullable=True)
    price_limit = Column(Numeric(30, 10), nullable=True)
    status = Column(String(30), nullable=False, server_default="pending")
    rejection_reason = Column(String(500), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
