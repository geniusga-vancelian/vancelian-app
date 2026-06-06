"""Modèles SQLAlchemy — outbox et transitions intent (Phase 2 S1)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class TransactionIntentTransition(Base):
    """Transition append-only de la machine à états intent."""

    __tablename__ = "transaction_intent_transitions"
    __table_args__ = (
        Index("ix_intent_transitions_intent_created", "intent_id", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    intent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.transaction_intents.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False)
    phase = Column(String(64), nullable=True)
    actor = Column(String(64), nullable=False, server_default="system")
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TransactionOutbox(Base):
    """File d'attente transactionnelle (pattern outbox)."""

    __tablename__ = "transaction_outbox"
    __table_args__ = (
        Index("ix_outbox_intent_created", "intent_id", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    intent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.transaction_intents.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(64), nullable=False)
    payload_json = Column(JSONB, nullable=True)
    status = Column(String(32), nullable=False, server_default="pending")
    attempt_count = Column(Integer, nullable=False, server_default="0")
    max_attempts = Column(Integer, nullable=False, server_default="10")
    next_retry_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by = Column(String(128), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
