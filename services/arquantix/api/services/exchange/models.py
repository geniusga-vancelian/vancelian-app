"""SQLAlchemy models for the Exchange module (crypto buy/sell, positions, settlement)."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class CryptoPosition(Base):
    __tablename__ = "crypto_positions"
    __table_args__ = (
        UniqueConstraint("client_id", "asset", name="uq_crypto_positions_client_asset"),
        Index("ix_crypto_positions_client_id", "client_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset = Column(String(20), nullable=False)
    balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    available_balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ExchangeFeeConfig(Base):
    __tablename__ = "exchange_fee_config"
    __table_args__ = (
        UniqueConstraint("asset", name="uq_exchange_fee_config_asset"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    asset = Column(String(20), nullable=False)
    fee_bps = Column(Integer, nullable=False, server_default="0")
    spread_bps = Column(Integer, nullable=False, server_default="50")
    active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ExchangeOrder(Base):
    __tablename__ = "exchange_orders"
    __table_args__ = (
        UniqueConstraint("external_reference", name="uq_exchange_orders_ext_ref"),
        Index("ix_exchange_orders_client_id", "client_id"),
        Index("ix_exchange_orders_asset", "asset"),
        Index("ix_exchange_orders_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    side = Column(String(10), nullable=False)
    asset = Column(String(20), nullable=False)
    amount_crypto = Column(Numeric(30, 18), nullable=False)
    amount_fiat = Column(Numeric(30, 10), nullable=False)
    price = Column(Numeric(30, 10), nullable=False)
    currency = Column(String(10), nullable=False, server_default="EUR")
    status = Column(String(20), nullable=False, server_default="pending")
    external_reference = Column(String(255), nullable=False)
    failure_reason = Column(Text, nullable=True)
    metadata_ = Column("metadata_", JSONB(astext_type=Text), nullable=False, server_default="{}")

    from_asset = Column(String(20), nullable=True)
    to_asset = Column(String(20), nullable=True)
    amount_from = Column(Numeric(30, 10), nullable=True)
    amount_to = Column(Numeric(30, 18), nullable=True)
    fee_amount = Column(Numeric(30, 18), nullable=True)
    fee_asset = Column(String(20), nullable=True)
    # PnL hardening: WAC cost basis consumed and realized PnL for SELL orders (auditability)
    cost_basis_consumed = Column(Numeric(30, 10), nullable=True)
    realized_pnl_generated = Column(Numeric(30, 10), nullable=True)
    # Swap crypto↔crypto: links SELL and BUY legs
    swap_group_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CryptoSettlementDelta(Base):
    __tablename__ = "crypto_settlement_deltas"
    __table_args__ = (
        UniqueConstraint("asset", "settlement_date", name="uq_crypto_settlement_delta_asset_date"),
        Index("ix_crypto_settlement_deltas_date", "settlement_date"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    asset = Column(String(20), nullable=False)
    settlement_date = Column(Date, nullable=False)
    delta_amount = Column(Numeric(30, 18), nullable=False, server_default="0")
    settled = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
