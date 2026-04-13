"""SQLAlchemy model for pe_audit_events (Hardening Subphase 1).

Append-only global audit trail. No UPDATE / DELETE paths.
"""
import uuid

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class AuditEvent(Base):
    __tablename__ = "pe_audit_events"
    __table_args__ = (
        Index("ix_pe_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_pe_audit_events_action", "action"),
        Index("ix_pe_audit_events_actor", "actor_type", "actor_id"),
        Index("ix_pe_audit_events_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)
    actor_type = Column(String(50), nullable=False, server_default="system")
    actor_id = Column(String(255), nullable=True)
    request_id = Column(String(255), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
