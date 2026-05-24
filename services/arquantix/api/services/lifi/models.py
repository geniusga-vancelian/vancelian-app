"""Modèle SQLAlchemy — sessions swap LI.FI."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class PersonWalletSwap(Base):
    __tablename__ = "person_wallet_swaps"
    __table_args__ = (
        Index("ix_person_wallet_swaps_person_id", "person_id"),
        Index("ix_person_wallet_swaps_status", "status"),
        Index("ix_person_wallet_swaps_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(32), nullable=False, server_default="PENDING")
    from_asset = Column(String(20), nullable=False)
    to_asset = Column(String(20), nullable=False)
    from_chain = Column(String(32), nullable=False)
    to_chain = Column(String(32), nullable=False)
    amount_in = Column(Numeric(30, 18), nullable=False)
    vancelian_fee = Column(Numeric(30, 18), nullable=True)
    vancelian_fee_bps = Column(Integer, nullable=True)
    network_fee = Column(Numeric(30, 18), nullable=True)
    network_fee_asset = Column(String(20), nullable=True)
    estimated_receive = Column(Numeric(30, 18), nullable=True)
    estimated_receive_min = Column(Numeric(30, 18), nullable=True)
    slippage_bps = Column(Integer, nullable=True)
    lifi_quote_id = Column(String(120), nullable=True)
    lifi_tool = Column(String(80), nullable=True)
    lifi_quote_raw = Column(JSONB, nullable=True)
    transaction_request = Column(JSONB, nullable=True)
    route_steps = Column(JSONB, nullable=True)
    tx_hash = Column(String(120), nullable=True)
    error_message = Column(Text, nullable=True)
    audit_log = Column(JSONB, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
