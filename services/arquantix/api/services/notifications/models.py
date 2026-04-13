"""Notification SQLAlchemy model."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_client_read", "client_id", "is_read"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("public.pe_clients.id"), nullable=False)
    type = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    is_read = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
