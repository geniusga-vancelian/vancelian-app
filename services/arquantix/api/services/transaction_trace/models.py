"""Modèle SQLAlchemy — transaction_trace_events (observabilité append-only)."""
from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class TransactionTraceEvent(Base):
    __tablename__ = "transaction_trace_events"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    event_type = Column(String(64), nullable=False)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="SET NULL"),
        nullable=True,
    )
    intent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.transaction_intents.id", ondelete="SET NULL"),
        nullable=True,
    )
    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.onchain_transaction_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    group_key = Column(String(128), nullable=True)
    idempotency_key = Column(String(255), nullable=True)
    protocol = Column(String(32), nullable=True)
    operation_type = Column(String(32), nullable=True)
    step_type = Column(String(32), nullable=True)
    status_from = Column(String(32), nullable=True)
    status_to = Column(String(32), nullable=True)
    tx_hash = Column(String(80), nullable=True)
    chain_id = Column(Integer, nullable=True)
    linked_table = Column(String(64), nullable=True)
    linked_id = Column(UUID(as_uuid=True), nullable=True)
    linked_reference_id = Column(String(80), nullable=True)
    source = Column(String(128), nullable=True)
    message = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
