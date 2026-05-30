"""Modèle SQLAlchemy — onchain_transaction_attempts (Phase 2)."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger,
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


class OnchainTransactionAttempt(Base):
    __tablename__ = "onchain_transaction_attempts"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            "step_type",
            name="uq_onchain_transaction_attempts_idempotency_step",
        ),
        Index("ix_attempts_person_created", "person_id", "created_at"),
        Index("ix_attempts_intent_id", "intent_id"),
        Index("ix_attempts_group_key", "group_key"),
        Index("ix_attempts_status", "status"),
        Index("ix_attempts_protocol_chain", "protocol", "chain_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    intent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.transaction_intents.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_intent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.transaction_intents.id", ondelete="SET NULL"),
        nullable=True,
    )
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_crypto_wallet_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.person_crypto_wallets.id", ondelete="SET NULL"),
        nullable=True,
    )

    chain_id = Column(Integer, nullable=False)
    protocol = Column(String(32), nullable=False)
    operation_type = Column(String(32), nullable=False)
    step_type = Column(String(32), nullable=False)
    step_index = Column(Integer, nullable=False, server_default="0")
    group_key = Column(String(128), nullable=True)
    idempotency_key = Column(String(255), nullable=False)

    status = Column(String(32), nullable=False, server_default="prepared")

    tx_hash = Column(String(80), nullable=True)
    nonce = Column(BigInteger, nullable=True)
    from_address = Column(String(80), nullable=True)
    to_address = Column(String(80), nullable=True)
    log_index = Column(Integer, nullable=True)

    asset_in = Column(String(32), nullable=True)
    asset_out = Column(String(32), nullable=True)
    amount_in = Column(Numeric(30, 18), nullable=True)
    amount_out_expected = Column(Numeric(30, 18), nullable=True)
    amount_out_actual = Column(Numeric(30, 18), nullable=True)

    block_number = Column(BigInteger, nullable=True)
    block_timestamp = Column(DateTime(timezone=True), nullable=True)
    gas_used = Column(BigInteger, nullable=True)

    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    raw_request_json = Column(JSONB, nullable=True)
    raw_signed_payload_json = Column(JSONB, nullable=True)
    raw_submission_json = Column(JSONB, nullable=True)
    raw_receipt_json = Column(JSONB, nullable=True)
    raw_revert_json = Column(JSONB, nullable=True)

    linked_table = Column(String(64), nullable=True)
    linked_id = Column(UUID(as_uuid=True), nullable=True)
    linked_reference_id = Column(String(80), nullable=True)

    metadata_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
