"""SQLAlchemy models — ledger wallet Privy (dépôts + soldes on-chain utilisateur)."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
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


class PrivyWebhookEvent(Base):
    __tablename__ = "privy_webhook_events"
    __table_args__ = (
        Index("ix_privy_webhook_events_status", "processing_status"),
        Index("ix_privy_webhook_events_received", "received_at"),
        Index("ix_privy_webhook_events_event_type", "event_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    svix_id = Column(String(255), nullable=True, unique=True)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    event_type = Column(String(100), nullable=False)
    external_reference = Column(String(255), nullable=True)
    payload_raw = Column(JSONB, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    processing_status = Column(String(20), nullable=False, server_default="received")
    error_message = Column(Text, nullable=True)
    linked_deposit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.person_wallet_deposits.id", ondelete="SET NULL"),
        nullable=True,
    )
    retry_count = Column(Integer, nullable=False, server_default="0")
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class PersonWalletDeposit(Base):
    __tablename__ = "person_wallet_deposits"
    __table_args__ = (
        UniqueConstraint(
            "chain_id",
            "tx_hash",
            "log_index",
            name="uq_person_wallet_deposits_chain_tx_log",
        ),
        Index("ix_person_wallet_deposits_person_id", "person_id"),
        Index("ix_person_wallet_deposits_wallet_id", "person_crypto_wallet_id"),
        Index("ix_person_wallet_deposits_asset", "asset"),
        Index("ix_person_wallet_deposits_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_crypto_wallet_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.person_crypto_wallets.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    pe_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    privy_webhook_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.privy_webhook_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_kind = Column(String(40), nullable=False, server_default="privy_deposit_in")
    direction = Column(String(10), nullable=False, server_default="credit")
    asset = Column(String(20), nullable=False)
    amount = Column(Numeric(30, 18), nullable=False)
    chain_type = Column(String(20), nullable=False)
    chain_id = Column(Integer, nullable=True)
    tx_hash = Column(String(80), nullable=False)
    log_index = Column(Integer, nullable=False, server_default="0")
    block_number = Column(Integer, nullable=True)
    from_address = Column(String(80), nullable=True)
    to_address = Column(String(80), nullable=False)
    confirmations = Column(Integer, nullable=False, server_default="0")
    status = Column(String(20), nullable=False, server_default="confirmed")
    idempotency_key = Column(String(255), nullable=True, unique=True)
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    confirmed_at = Column(DateTime(timezone=True), nullable=True)


class PersonWalletBalance(Base):
    __tablename__ = "person_wallet_balances"
    __table_args__ = (
        UniqueConstraint(
            "person_crypto_wallet_id",
            "asset",
            name="uq_person_wallet_balances_wallet_asset",
        ),
        Index("ix_person_wallet_balances_person_id", "person_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_crypto_wallet_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.person_crypto_wallets.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset = Column(String(20), nullable=False)
    balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    available_balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    last_synced_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sync_source = Column(String(40), nullable=False, server_default="privy_webhook")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PersonWalletReconciliationRun(Base):
    __tablename__ = "person_wallet_reconciliation_runs"
    __table_args__ = (
        Index("ix_person_wallet_reconciliation_runs_person_id", "person_id"),
        Index("ix_person_wallet_reconciliation_runs_started_at", "started_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    scope = Column(String(20), nullable=False, server_default="person")
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=True,
    )
    status = Column(String(40), nullable=False, server_default="running")
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    items_checked = Column(Integer, nullable=False, server_default="0")
    matched_count = Column(Integer, nullable=False, server_default="0")
    healed_count = Column(Integer, nullable=False, server_default="0")
    chain_ahead_count = Column(Integer, nullable=False, server_default="0")
    ledger_ahead_count = Column(Integer, nullable=False, server_default="0")
    mismatch_count = Column(Integer, nullable=False, server_default="0")
    unresolved_count = Column(Integer, nullable=False, server_default="0")
    replayed_webhooks = Column(Integer, nullable=False, server_default="0")
    summary_json = Column(JSONB, nullable=True)


class PersonWalletReconciliationItem(Base):
    __tablename__ = "person_wallet_reconciliation_items"
    __table_args__ = (
        Index("ix_person_wallet_reconciliation_items_run_id", "run_id"),
        Index("ix_person_wallet_reconciliation_items_person_id", "person_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.person_wallet_reconciliation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    wallet_address = Column(String(80), nullable=False)
    chain_id = Column(Integer, nullable=True)
    chain_label = Column(String(80), nullable=True)
    asset = Column(String(20), nullable=False)
    ledger_balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    on_chain_balance = Column(Numeric(30, 18), nullable=False, server_default="0")
    delta = Column(Numeric(30, 18), nullable=False, server_default="0")
    status = Column(String(40), nullable=False)
    action_taken = Column(String(40), nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
