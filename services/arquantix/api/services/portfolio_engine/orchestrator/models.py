"""SQLAlchemy model for pe_orchestration_runs (Phase 8 — Rebalance Orchestrator).

Run rows are created at cycle start and updated at completion.
After completed_at is set, rows are effectively immutable.
"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class OrchestrationRun(Base):
    __tablename__ = "pe_orchestration_runs"
    __table_args__ = (
        Index("ix_pe_orchestration_runs_portfolio_id", "portfolio_id"),
        Index("ix_pe_orchestration_runs_status", "status"),
        Index("ix_pe_orchestration_runs_started_at", "started_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode = Column(String(20), nullable=False)
    signals_detected = Column(Integer, nullable=False, server_default="0")
    actions_taken = Column(Integer, nullable=False, server_default="0")
    rebalance_preview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_rebalance_previews.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(20), nullable=False)
    abort_reason = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
