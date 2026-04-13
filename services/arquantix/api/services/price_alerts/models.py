"""PriceAlert SQLAlchemy model."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    __table_args__ = (
        Index("ix_price_alerts_client_asset_status", "client_id", "asset", "status"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("public.pe_clients.id"), nullable=False)
    asset = Column(String(20), nullable=False)
    target_price = Column(Numeric(20, 8), nullable=False)
    direction = Column(String(10), nullable=False)
    price_source = Column(String(10), nullable=False, server_default="mid")
    status = Column(String(20), nullable=False, server_default="active")
    action_type = Column(String(20), nullable=False, server_default="alert")
    trigger_mode = Column(String(20), nullable=False, server_default="once")
    trigger_count = Column(Integer, nullable=False, server_default="0")
    order_payload = Column(JSONB, nullable=True)
    cooldown_seconds = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    triggered_price = Column(Numeric(20, 8), nullable=True)
    execution_status = Column(String(20), nullable=True)
    metadata_ = Column(JSONB, nullable=True)
