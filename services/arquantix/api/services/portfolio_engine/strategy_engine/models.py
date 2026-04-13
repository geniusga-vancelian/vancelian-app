"""SQLAlchemy model for pe_strategy_evaluations (Phase 7 — Strategy Engine).

Append-only table. No UPDATE / DELETE paths.
"""
import uuid

from sqlalchemy import Column, ForeignKey, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class StrategyEvaluation(Base):
    __tablename__ = "pe_strategy_evaluations"
    __table_args__ = (
        Index("ix_pe_strategy_evaluations_portfolio_id", "portfolio_id"),
        Index("ix_pe_strategy_evaluations_instance_id", "strategy_instance_id"),
        Index("ix_pe_strategy_evaluations_signal_type", "signal_type"),
        Index("ix_pe_strategy_evaluations_eval_ts", "evaluation_timestamp"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    strategy_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_strategy_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    strategy_type = Column(String(50), nullable=False)
    signal_type = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, server_default="info")
    details = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    evaluation_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
