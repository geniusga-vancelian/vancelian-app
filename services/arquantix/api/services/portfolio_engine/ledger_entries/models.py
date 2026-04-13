"""SQLAlchemy model for the pe_ledger_entries table (Portfolio Engine — accounting layer).

This table is APPEND-ONLY. No UPDATE or DELETE is ever permitted.
"""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class LedgerEntry(Base):
    __tablename__ = "pe_ledger_entries"
    __table_args__ = (
        Index("ix_pe_ledger_entries_account_effective", "account_id", "effective_at"),
        Index("ix_pe_ledger_entries_reference", "reference_type", "reference_id"),
        Index("ix_pe_ledger_entries_counterpart", "counterpart_entry_id"),
        Index("ix_pe_ledger_entries_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entry_type = Column(String(10), nullable=False)
    amount = Column(Numeric(30, 10), nullable=False)
    currency = Column(String(20), nullable=False)
    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reference_type = Column(String(50), nullable=False)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    counterpart_entry_id = Column(UUID(as_uuid=True), nullable=True)
    description = Column(String(500), nullable=True)
    effective_at = Column(DateTime(timezone=True), nullable=False)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
