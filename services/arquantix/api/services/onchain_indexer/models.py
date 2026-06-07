"""Modèles SQLAlchemy — événements on-chain bruts + intents (squelette)."""
from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class RawOnChainEvent(Base):
    __tablename__ = "raw_onchain_events"
    __table_args__ = (
        UniqueConstraint(
            "chain_id",
            "tx_hash",
            "log_index",
            name="uq_raw_onchain_events_chain_tx_log",
        ),
        Index("ix_raw_onchain_events_wallet_chain", "wallet_address", "chain_id"),
        Index("ix_raw_onchain_events_tx_hash", "tx_hash"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    chain_id = Column(Integer, nullable=False)
    block_number = Column(BigInteger, nullable=True)
    tx_hash = Column(String(80), nullable=False)
    log_index = Column(Integer, nullable=False, server_default="0")
    contract_address = Column(String(80), nullable=True)
    event_type = Column(String(40), nullable=False, server_default="erc20_transfer")
    wallet_address = Column(String(80), nullable=False)
    asset = Column(String(20), nullable=False)
    amount_raw = Column(Numeric(78, 0), nullable=False)
    payload_json = Column(JSONB, nullable=True)
    consumed_by_correction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.reconciliation_corrections.id", ondelete="SET NULL"),
        nullable=True,
    )
    parsed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class OnchainIndexerCheckpoint(Base):
    """Curseur de scan par chaîne / indexer (Phase 6)."""

    __tablename__ = "onchain_indexer_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "chain_id",
            "indexer_name",
            name="uq_onchain_indexer_checkpoints_chain_indexer",
        ),
        Index("ix_onchain_indexer_checkpoints_chain_id", "chain_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    chain_id = Column(Integer, nullable=False)
    indexer_name = Column(String(64), nullable=False)
    last_scanned_block = Column(BigInteger, nullable=False, server_default="0")
    status = Column(String(32), nullable=False, server_default="idle")
    metadata_json = Column(JSONB, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TransactionIntent(Base):
    """Intent transactionnel cross-produit (Phase 7 — traçabilité, pas ledger)."""

    __tablename__ = "transaction_intents"
    __table_args__ = (
        UniqueConstraint(
            "person_id",
            "product_type",
            "operation_type",
            "idempotency_key",
            name="uq_transaction_intents_person_product_op_key",
        ),
        Index("ix_transaction_intents_person_id", "person_id"),
        Index("ix_transaction_intents_tx_hash", "tx_hash"),
        Index("ix_transaction_intents_linked", "linked_table", "linked_id"),
        Index("ix_transaction_intents_parent_intent_id", "parent_intent_id"),
        Index("ix_transaction_intents_bundle_execution_id", "bundle_execution_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    parent_intent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.transaction_intents.id", ondelete="CASCADE"),
        nullable=True,
    )
    intent_role = Column(String(16), nullable=True)
    leg_index = Column(Integer, nullable=True)
    bundle_execution_id = Column(UUID(as_uuid=True), nullable=True)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="SET NULL"),
        nullable=True,
    )
    wallet_address = Column(String(80), nullable=True)
    chain_id = Column(Integer, nullable=True)
    product_type = Column(String(40), nullable=False)
    operation_type = Column(String(32), nullable=False, server_default="swap")
    idempotency_key = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, server_default="created")
    tx_hash = Column(String(80), nullable=True)
    raw_onchain_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.raw_onchain_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_table = Column(String(64), nullable=True)
    linked_id = Column(UUID(as_uuid=True), nullable=True)
    linked_reference_id = Column(String(80), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    # Phase 2 S1 — orchestrateur (extensions non-breaking)
    correlation_id = Column(UUID(as_uuid=True), nullable=False, server_default=func.gen_random_uuid())
    current_phase = Column(String(64), nullable=False, server_default="created")
    requested_action = Column(String(32), nullable=True)
    assets_json = Column(JSONB, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    reconciliation_report_json = Column(JSONB, nullable=True)
    blocked_assets_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
