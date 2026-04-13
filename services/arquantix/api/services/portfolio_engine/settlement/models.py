"""SQLAlchemy model for the pe_settlement_instructions table (Portfolio Engine — settlement layer).

Core business fields (from_account_id, to_account_id, asset_id, amount) are immutable
after creation. Only status, timestamps, failure fields, and external_reference may be
updated after creation.
"""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class SettlementInstruction(Base):
    __tablename__ = "pe_settlement_instructions"
    __table_args__ = (
        Index("ix_pe_sett_order_id", "order_id"),
        Index("ix_pe_sett_trade_id", "trade_id"),
        Index("ix_pe_sett_group_id", "settlement_group_id"),
        Index("ix_pe_sett_from_account", "from_account_id"),
        Index("ix_pe_sett_to_account", "to_account_id"),
        Index("ix_pe_sett_asset_id", "asset_id"),
        Index("ix_pe_sett_status", "status"),
        Index("ix_pe_sett_scheduled_at", "scheduled_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    trade_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_trades.id", ondelete="RESTRICT"),
        nullable=True,
    )
    settlement_group_id = Column(UUID(as_uuid=True), nullable=True)
    settlement_type = Column(String(50), nullable=False)
    from_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount = Column(Numeric(30, 10), nullable=False)
    status = Column(String(30), nullable=False, server_default="pending")
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    settled_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String(500), nullable=True)
    external_reference = Column(String(255), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
