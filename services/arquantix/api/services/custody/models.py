"""SQLAlchemy models for the Custody module (fiat accounts, balances, transactions, webhooks)."""
import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, Numeric, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class CustodyProvider(Base):
    __tablename__ = "custody_providers"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(20), nullable=False)
    jurisdiction = Column(String(50), nullable=True)
    api_base_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, server_default="active")
    metadata_ = Column("metadata_", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CustodyAccount(Base):
    __tablename__ = "custody_accounts"
    __table_args__ = (
        Index("ix_custody_accounts_client_id", "client_id"),
        Index("ix_custody_accounts_provider_id", "provider_id"),
        Index("ix_custody_accounts_account_type", "account_type"),
        Index("ix_custody_accounts_ledger_account_id", "ledger_account_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.custody_providers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_type = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False)
    iban = Column(String(50), nullable=True)
    bic = Column(String(20), nullable=True)
    account_holder_name = Column(String(255), nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    ledger_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_ledger_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_master_account = Column(Boolean, nullable=False, server_default="false")
    status = Column(String(20), nullable=False, server_default="active")
    metadata_ = Column("metadata_", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CustodyAccountBalance(Base):
    __tablename__ = "custody_account_balances"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.custody_accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    available_balance = Column(Numeric(30, 10), nullable=False, server_default="0")
    pending_balance = Column(Numeric(30, 10), nullable=False, server_default="0")
    currency = Column(String(10), nullable=False)
    version = Column(Integer, nullable=False, server_default="1")
    last_updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CustodyTransaction(Base):
    __tablename__ = "custody_transactions"
    __table_args__ = (
        Index("ix_custody_transactions_account_id", "account_id"),
        Index("ix_custody_transactions_type", "transaction_type"),
        Index("ix_custody_transactions_created_at", "created_at"),
        Index("ix_custody_transactions_provider_id", "provider_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.custody_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.custody_providers.id", ondelete="RESTRICT"),
        nullable=True,
    )
    transaction_type = Column(String(30), nullable=False)
    transaction_kind = Column(String(30), nullable=True)
    direction = Column(String(10), nullable=False)
    amount = Column(Numeric(30, 10), nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, server_default="pending")
    external_reference = Column(String(255), nullable=True)
    provider_reference = Column(String(255), nullable=True)
    failure_reason = Column(Text, nullable=True)
    reversal_of_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.custody_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_ = Column("metadata_", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())


class CustodyWebhookEvent(Base):
    __tablename__ = "custody_webhook_events"
    __table_args__ = (
        Index("ix_custody_webhook_events_provider_ref", "provider_id", "external_reference"),
        Index("ix_custody_webhook_events_status", "processing_status"),
        Index("ix_custody_webhook_events_received", "received_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.custody_providers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type = Column(String(50), nullable=False)
    external_reference = Column(String(255), nullable=True)
    payload_raw = Column(JSONB, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    processing_status = Column(String(20), nullable=False, server_default="received")
    error_message = Column(Text, nullable=True)
    linked_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.custody_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    retry_count = Column(Integer, nullable=False, server_default="0")
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata_", JSONB, nullable=False, server_default="{}")
