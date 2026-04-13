"""SQLAlchemy model for the pe_execution_instructions table (Portfolio Engine — execution layer).

Core business fields (order_id, venue, execution_type, instrument_id, side, quantity, amount,
price_limit, currency) are immutable after creation. Only status, timestamps, fill progress,
venue references, failure fields, and response_payload may be updated.
"""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class ExecutionInstruction(Base):
    __tablename__ = "pe_execution_instructions"
    __table_args__ = (
        Index("ix_pe_exec_order_id", "order_id"),
        Index("ix_pe_exec_parent_id", "parent_execution_id"),
        Index("ix_pe_exec_venue", "venue"),
        Index("ix_pe_exec_instrument_id", "instrument_id"),
        Index("ix_pe_exec_status", "status"),
        Index("ix_pe_exec_venue_order_id", "venue_order_id"),
        Index("ix_pe_exec_requested_at", "requested_at"),
        Index("ix_pe_exec_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_execution_instructions.id", ondelete="SET NULL"),
        nullable=True,
    )
    venue = Column(String(100), nullable=False)
    execution_type = Column(String(50), nullable=False)
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="SET NULL"),
        nullable=True,
    )
    side = Column(String(10), nullable=True)
    quantity = Column(Numeric(30, 10), nullable=True)
    amount = Column(Numeric(30, 10), nullable=True)
    price_limit = Column(Numeric(30, 10), nullable=True)
    currency = Column(String(20), nullable=True)
    status = Column(String(30), nullable=False, server_default="pending")
    venue_order_id = Column(String(255), nullable=True)
    filled_quantity = Column(Numeric(30, 10), nullable=True, server_default="0")
    average_fill_price = Column(Numeric(30, 10), nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String(500), nullable=True)
    response_payload = Column(JSONB(astext_type=Text), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
