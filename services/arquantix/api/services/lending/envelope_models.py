"""Investment Envelope models — Phase 2A.16.

Encapsulates the full lifecycle of an investment entry:
  User Wallet → Envelope (conversion + fees) → Strategy (lending / bundle)
"""
from __future__ import annotations

from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from database import Base


class InvestmentEnvelope(Base):
    __tablename__ = "investment_envelopes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    client_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    reference_id = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False, server_default="active")
    metadata_ = Column("metadata_", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    entries = relationship("InvestmentEnvelopeEntry", back_populates="envelope", lazy="joined")


class InvestmentEnvelopeEntry(Base):
    __tablename__ = "investment_envelope_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    envelope_id = Column(UUID(as_uuid=True), ForeignKey("investment_envelopes.id"), nullable=False, index=True)
    commitment_id = Column(UUID(as_uuid=True), nullable=True)

    entry_asset = Column(String(20), nullable=False)
    entry_amount = Column(Numeric(precision=30, scale=10), nullable=False)

    target_asset = Column(String(20), nullable=False)
    converted_amount = Column(Numeric(precision=30, scale=10), nullable=False)

    fx_rate = Column(Numeric(precision=20, scale=10), nullable=True)
    conversion_type = Column(String(20), nullable=False, server_default="none")
    conversion_fee = Column(Numeric(precision=30, scale=10), nullable=False, server_default="0")
    platform_fee = Column(Numeric(precision=30, scale=10), nullable=False, server_default="0")
    net_allocated = Column(Numeric(precision=30, scale=10), nullable=False)

    external_reference = Column(String(255), nullable=True)
    conversion_details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    envelope = relationship("InvestmentEnvelope", back_populates="entries")
