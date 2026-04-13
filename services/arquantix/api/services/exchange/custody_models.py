"""SQLAlchemy models for crypto custody layer (technical wallets per asset)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class CryptoCustodyAccount(Base):
    """Technical custody account per asset (clients_pool or settlement_wallet)."""

    __tablename__ = "crypto_custody_accounts"
    __table_args__ = (
        UniqueConstraint("asset", "account_type", name="uq_crypto_custody_accounts_asset_type"),
        Index("ix_crypto_custody_accounts_asset", "asset"),
        Index("ix_crypto_custody_accounts_account_type", "account_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    asset = Column(String(20), nullable=False)
    account_type = Column(String(50), nullable=False)  # clients_pool | settlement_wallet
    provider = Column(String(50), nullable=False)
    provider_account_id = Column(String(255), nullable=True)
    label = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, server_default="active")
    metadata_ = Column("metadata_", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CryptoCustodyBalance(Base):
    """Balance for a crypto custody account: actual (provider) vs expected (internal)."""

    __tablename__ = "crypto_custody_balances"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_crypto_custody_balances_account_id"),
        Index("ix_crypto_custody_balances_account_id", "account_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.crypto_custody_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset = Column(String(20), nullable=False)
    actual_balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    expected_balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    updated_from_provider_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
