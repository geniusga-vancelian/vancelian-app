"""SQLAlchemy model for pe_reconciliation_reports (Hardening Subphase 3).

Append-only table. No UPDATE / DELETE.
"""
import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class ReconciliationReport(Base):
    __tablename__ = "pe_reconciliation_reports"
    __table_args__ = (
        Index("ix_pe_recon_reports_type", "reconciliation_type"),
        Index("ix_pe_recon_reports_scope", "scope_type", "scope_id"),
        Index("ix_pe_recon_reports_status", "status"),
        Index("ix_pe_recon_reports_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    reconciliation_type = Column(String(100), nullable=False)
    scope_type = Column(String(100), nullable=False)
    scope_id = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False)
    differences_found = Column(Integer, nullable=False, server_default="0")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
