"""SQLAlchemy model for pe_idempotency_keys (Hardening Subphase 1).

Prevents duplicate processing of critical mutating requests.
"""
import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class IdempotencyKey(Base):
    __tablename__ = "pe_idempotency_keys"
    __table_args__ = (
        Index(
            "uq_pe_idempotency_key_scope",
            "idempotency_key",
            "scope",
            unique=True,
        ),
        Index("ix_pe_idempotency_keys_expires_at", "expires_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    idempotency_key = Column(String(255), nullable=False)
    scope = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
