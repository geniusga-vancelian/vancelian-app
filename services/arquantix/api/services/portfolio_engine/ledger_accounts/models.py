"""SQLAlchemy model for the pe_ledger_accounts table (Portfolio Engine — accounting layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class LedgerAccount(Base):
    __tablename__ = "pe_ledger_accounts"
    __table_args__ = (
        Index("ix_pe_ledger_accounts_client_id", "client_id"),
        Index("ix_pe_ledger_accounts_account_type", "account_type"),
        Index("ix_pe_ledger_accounts_currency", "currency"),
        Index("ix_pe_ledger_accounts_wallet_container_id", "wallet_container_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    account_type = Column(String(50), nullable=False)
    account_code = Column(String(100), unique=True, nullable=False)
    label = Column(String(255), nullable=False)
    currency = Column(String(20), nullable=False)
    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    wallet_container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_wallet_containers.id", ondelete="SET NULL"),
        nullable=True,
    )
    balance = Column(Numeric(30, 10), nullable=False, server_default="0")
    status = Column(String(30), nullable=False, server_default="active")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
