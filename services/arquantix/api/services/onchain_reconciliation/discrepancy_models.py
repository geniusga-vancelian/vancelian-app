"""Modèles anomalies / corrections (Phase 4)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class ReconciliationDiscrepancy(Base):
    __tablename__ = "reconciliation_discrepancies"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_reconciliation_discrepancies_fingerprint"),
        Index("ix_reconciliation_discrepancies_person_status", "person_id", "status"),
        Index("ix_reconciliation_discrepancies_layer", "layer"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    wallet_address = Column(String(80), nullable=True)
    layer = Column(String(32), nullable=False)
    asset = Column(String(20), nullable=True)
    discrepancy_type = Column(String(64), nullable=False)
    db_amount = Column(Numeric(30, 18), nullable=True)
    onchain_amount = Column(Numeric(30, 18), nullable=True)
    delta = Column(Numeric(30, 18), nullable=True)
    severity = Column(String(10), nullable=False, server_default="P2")
    status = Column(String(20), nullable=False, server_default="open")
    reference_type = Column(String(40), nullable=True)
    reference_id = Column(String(255), nullable=True)
    fingerprint = Column(String(64), nullable=False)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class ReconciliationCorrection(Base):
    """Audit trail des corrections futures — stub Phase 4 (pas d'apply destructif)."""

    __tablename__ = "reconciliation_corrections"
    __table_args__ = (
        Index("ix_reconciliation_corrections_discrepancy_id", "discrepancy_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    discrepancy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.reconciliation_discrepancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    action = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, server_default="preview")
    before_json = Column(JSONB, nullable=True)
    after_json = Column(JSONB, nullable=True)
    requested_by = Column(String(255), nullable=True)
    approved_by = Column(String(255), nullable=True)
    dry_run = Column(Boolean, nullable=False, server_default="true")
    applied_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
