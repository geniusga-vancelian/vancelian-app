"""Modèles observabilité DeFi — job runs (Phase 9)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class DefiObservabilityJobRun(Base):
    __tablename__ = "defi_observability_job_runs"
    __table_args__ = (
        Index("ix_defi_obs_job_runs_job_name", "job_name"),
        Index("ix_defi_obs_job_runs_started_at", "started_at"),
        Index("ix_defi_obs_job_runs_status", "status"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    job_name = Column(String(80), nullable=False)
    status = Column(String(32), nullable=False, server_default="running")
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    summary_json = Column(JSONB, nullable=False, server_default="{}")
    error_json = Column(JSONB, nullable=True)
