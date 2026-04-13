"""SQLAlchemy model for the pe_trading_fee_configs table."""
import uuid

from sqlalchemy import Column, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class TradingFeeConfig(Base):
    __tablename__ = "pe_trading_fee_configs"
    __table_args__ = (
        Index("ix_pe_trading_fee_configs_scope", "scope_type", "scope_id"),
        Index("ix_pe_trading_fee_configs_status", "status"),
        Index("ix_pe_trading_fee_configs_fee_type", "fee_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    scope_type = Column(String(30), nullable=False)
    scope_id = Column(UUID(as_uuid=True), nullable=True)
    fee_type = Column(String(30), nullable=False, server_default="trading")
    fee_rate = Column(Numeric(12, 8), nullable=False)
    min_fee = Column(Numeric(30, 10), nullable=True)
    max_fee = Column(Numeric(30, 10), nullable=True)
    status = Column(String(20), nullable=False, server_default="active")
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_to = Column(DateTime(timezone=True), nullable=True)

    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
