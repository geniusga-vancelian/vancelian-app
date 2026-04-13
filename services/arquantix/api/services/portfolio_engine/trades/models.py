"""SQLAlchemy model for the pe_trades table (Portfolio Engine — transaction layer).

This table is IMMUTABLE. No UPDATE or DELETE is ever permitted.
"""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class Trade(Base):
    __tablename__ = "pe_trades"
    __table_args__ = (
        Index("ix_pe_trades_order_id", "order_id"),
        Index("ix_pe_trades_instrument_id", "instrument_id"),
        Index("ix_pe_trades_executed_at", "executed_at"),
        Index("ix_pe_trades_external_trade_id", "external_trade_id"),
        Index("ix_pe_trades_execution_instruction_id", "execution_instruction_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    execution_instruction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_execution_instructions.id", ondelete="SET NULL"),
        nullable=True,
    )
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    side = Column(String(10), nullable=False)
    quantity = Column(Numeric(30, 10), nullable=False)
    price = Column(Numeric(30, 10), nullable=False)
    gross_amount = Column(Numeric(30, 10), nullable=False)
    fee_amount = Column(Numeric(30, 10), nullable=False, server_default="0")
    net_amount = Column(Numeric(30, 10), nullable=False)
    currency = Column(String(20), nullable=False)
    counterparty = Column(String(100), nullable=True)
    external_trade_id = Column(String(255), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=False)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
