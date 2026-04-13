"""SQLAlchemy model for the pe_instruments table (Portfolio Engine — registry layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Instrument(Base):
    __tablename__ = "pe_instruments"
    __table_args__ = (
        Index("ix_pe_instruments_asset_id", "asset_id"),
        Index("ix_pe_instruments_instrument_type", "instrument_type"),
        Index("ix_pe_instruments_metadata", "metadata", postgresql_using="gin"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("public.pe_assets.id", ondelete="RESTRICT"), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    instrument_type = Column(String(50), nullable=False)
    liquidity_profile = Column(String(50), nullable=True)
    lockup_period_days = Column(Integer, nullable=True)
    valuation_method = Column(String(50), nullable=True)
    yield_source = Column(String(100), nullable=True)
    provider = Column(String(100), nullable=True)
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    asset = relationship("Asset", lazy="select")
