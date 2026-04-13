"""SQLAlchemy model for pe_job_runs (Hardening Subphase 2).

Tracks rebuild/replay and administrative job executions.
Status and timestamps may be updated during the job lifecycle.
"""
import uuid

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class JobRun(Base):
    __tablename__ = "pe_job_runs"
    __table_args__ = (
        Index("ix_pe_job_runs_job_type", "job_type"),
        Index("ix_pe_job_runs_scope", "scope_type", "scope_id"),
        Index("ix_pe_job_runs_status", "status"),
        Index("ix_pe_job_runs_started_at", "started_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    job_type = Column(String(100), nullable=False)
    scope_type = Column(String(100), nullable=False)
    scope_id = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False, server_default="started")
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
