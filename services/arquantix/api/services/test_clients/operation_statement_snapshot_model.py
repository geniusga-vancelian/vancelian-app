"""Persistance des snapshots documentaires ``OperationStatementPayload`` (PR5)."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text as SaText, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class ClientOperationStatementSnapshot(Base):
    """
    Une ligne par (client, source) : vérité documentaire figée au premier PDF réussi.
    """

    __tablename__ = "client_operation_statement_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "source_system",
            "source_id",
            name="uq_client_operation_statement_snapshots_client_source",
        ),
        Index("ix_client_operation_statement_snapshots_client_id", "client_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_system = Column(String(20), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    schema_version = Column(String(32), nullable=False)
    payload_json = Column(JSONB(astext_type=SaText()), nullable=False)
    content_sha256 = Column(SaText(), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    pdf_sha256 = Column(SaText(), nullable=True)
