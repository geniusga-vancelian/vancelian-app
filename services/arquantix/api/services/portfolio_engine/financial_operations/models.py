"""Modèle SQLAlchemy — portfolio_financial_operations (PR-4)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class PortfolioFinancialOperation(Base):
    """Slot d'exclusion mutuelle par portefeuille — 1 opération financière active."""

    __tablename__ = "portfolio_financial_operations"
    __table_args__ = (
        Index("ix_pfo_portfolio_id", "portfolio_id"),
        Index("ix_pfo_expires_at", "expires_at"),
        Index("ix_pfo_execution_id", "execution_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_type = Column(String(40), nullable=False)
    execution_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(32), nullable=False, server_default="ACTIVE")
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
