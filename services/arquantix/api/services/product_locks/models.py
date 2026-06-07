"""Modèle SQLAlchemy — transaction_product_locks (S4 L1)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class TransactionProductLock(Base):
    """Lock pessimiste produit / asset / scope (ADR 001 §5bis).

    Acquisition / release via ``services.product_locks.service`` (S4 L2).
    """

    __tablename__ = "transaction_product_locks"
    __table_args__ = (
        Index("ix_product_locks_intent_id", "intent_id"),
        Index("ix_product_locks_person_wallet_asset", "person_id", "wallet_id", "asset"),
        Index("ix_product_locks_expires_at", "expires_at"),
        Index("ix_product_locks_lock_key", "lock_key"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    wallet_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.person_crypto_wallets.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset = Column(String(32), nullable=False)
    scope = Column(String(32), nullable=False)
    product_type = Column(String(40), nullable=False)
    intent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.transaction_intents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(32), nullable=False, server_default="active")
    lock_key = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
