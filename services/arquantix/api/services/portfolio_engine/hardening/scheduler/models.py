"""SQLAlchemy model for pe_scheduled_jobs (Hardening Subphase 4).

Stores job scheduling definitions. Mutable (is_enabled, last_run_at, next_run_at, etc.).
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class ScheduledJob(Base):
    __tablename__ = "pe_scheduled_jobs"
    __table_args__ = (
        Index("ix_pe_scheduled_jobs_job_type", "job_type"),
        Index("ix_pe_scheduled_jobs_is_enabled", "is_enabled"),
        Index("ix_pe_scheduled_jobs_next_run_at", "next_run_at"),
        Index("ix_pe_scheduled_jobs_scope", "scope_type", "scope_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    job_name = Column(String(255), nullable=False)
    job_type = Column(String(100), nullable=False)
    scope_type = Column(String(100), nullable=False)
    scope_id = Column(String(255), nullable=True)
    schedule_type = Column(String(30), nullable=False, server_default="interval")
    cron_expression = Column(String(100), nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default="true")
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
