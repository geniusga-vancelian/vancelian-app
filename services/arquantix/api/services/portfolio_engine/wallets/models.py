"""SQLAlchemy model for the pe_wallet_containers table (Portfolio Engine — ledger layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class WalletContainer(Base):
    __tablename__ = "pe_wallet_containers"
    __table_args__ = (
        Index("ix_pe_wallet_containers_client_id", "client_id"),
        Index("ix_pe_wallet_containers_portfolio_id", "portfolio_id"),
        Index("ix_pe_wallet_containers_wallet_type", "wallet_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    # TODO: add FK to pe_clients.id when the clients module is implemented.
    client_id = Column(UUID(as_uuid=True), nullable=True)
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="SET NULL"),
        nullable=True,
    )
    wallet_type = Column(String(50), nullable=False)
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="SET NULL"),
        nullable=True,
    )
    custody_provider = Column(String(100), nullable=True)
    blockchain_address = Column(String(255), nullable=True)
    ledger_account_ref = Column(String(255), nullable=True)
    jurisdiction = Column(String(50), nullable=True)
    status = Column(String(30), nullable=False, server_default="active")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", lazy="select")
    instrument = relationship("Instrument", lazy="select")
