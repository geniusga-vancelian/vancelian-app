"""SQLAlchemy model for the pe_assets table (Portfolio Engine — registry layer)."""
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class Asset(Base):
    __tablename__ = "pe_assets"
    __table_args__ = (
        Index("ix_pe_assets_asset_type", "asset_type"),
        Index("ix_pe_assets_metadata", "metadata", postgresql_using="gin"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    symbol = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(50), nullable=False)
    valuation_source = Column(String(100), nullable=True)
    liquidity_profile = Column(String(50), nullable=True)
    risk_profile = Column(String(50), nullable=True)
    supports_staking = Column(Boolean, nullable=False, server_default="false")
    supports_collateral = Column(Boolean, nullable=False, server_default="false")
    supports_borrowing = Column(Boolean, nullable=False, server_default="false")
    supports_yield = Column(Boolean, nullable=False, server_default="false")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
