"""ORM — exécutions de cost basis normalisées (V2)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base

D18 = Numeric(30, 18)
D10 = Numeric(30, 10)


class CostBasisExecution(Base):
    """Fait d'exécution figé — source unique pour le WAC / PRU."""

    __tablename__ = "cost_basis_executions"
    __table_args__ = (
        UniqueConstraint(
            "provider_source",
            "provider_execution_id",
            name="uq_cost_basis_executions_provider",
        ),
        Index("ix_cost_basis_executions_client_asset", "client_id", "position_asset"),
        Index("ix_cost_basis_executions_executed_at", "executed_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id = Column(UUID(as_uuid=True), nullable=True)
    position_asset = Column(String(20), nullable=False)
    event_kind = Column(String(16), nullable=False)
    quantity = Column(D18, nullable=False)
    native_quote_asset = Column(String(20), nullable=False)
    native_execution_price = Column(D18, nullable=False)
    native_notional = Column(D18, nullable=False)
    execution_price_usdc = Column(D18, nullable=False)
    execution_notional_usdc = Column(D18, nullable=False)
    execution_price_eur = Column(D18, nullable=False)
    execution_notional_eur = Column(D18, nullable=False)
    eurusd_rate_at_execution = Column(D10, nullable=False)
    fees_usdc = Column(D18, nullable=False, server_default="0")
    fees_eur = Column(D18, nullable=False, server_default="0")
    provider_source = Column(String(32), nullable=False)
    provider_execution_id = Column(String(255), nullable=False)
    tx_hash = Column(String(120), nullable=True)
    counterparty_asset = Column(String(20), nullable=True)
    portfolio_scope = Column(String(32), nullable=True)
    portfolio_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_ = Column("metadata_", JSONB(astext_type=Text), nullable=False, server_default="{}")
    executed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
