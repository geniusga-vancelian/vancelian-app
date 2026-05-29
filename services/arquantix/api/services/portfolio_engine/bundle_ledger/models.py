"""Modèle ORM — journal append-only ``bundle_ledger_entries`` (Phase 4A)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base


class BundleLedgerEntry(Base):
    """Entrée immutable du journal bundle — aucune mise à jour destructive."""

    __tablename__ = "bundle_ledger_entries"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_bundle_ledger_entries_idempotency_key"),
        Index("ix_bundle_ledger_entries_portfolio_created", "bundle_portfolio_id", "created_at"),
        Index("ix_bundle_ledger_entries_person_created", "person_id", "created_at"),
        Index("ix_bundle_ledger_entries_batch_id", "batch_id"),
        Index("ix_bundle_ledger_entries_event_type", "event_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), nullable=False)
    bundle_portfolio_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(64), nullable=False)
    asset_symbol = Column(String(32), nullable=False)
    asset_instrument_id = Column(UUID(as_uuid=True), nullable=True)
    quantity = Column(Numeric(30, 10), nullable=False)
    amount_usd = Column(Numeric(30, 10), nullable=True)
    direction = Column(String(16), nullable=False)
    source_system = Column(String(32), nullable=False)
    source_id = Column(String(255), nullable=True)
    batch_id = Column(String(255), nullable=True)
    leg_id = Column(String(255), nullable=True)
    transaction_intent_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(32), nullable=False, server_default="confirmed")
    idempotency_key = Column(String(512), nullable=False)
    metadata_ = Column("metadata", JSONB(astext_type=Text()), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
