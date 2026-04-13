"""SQLAlchemy model for the pe_position_atoms table (Portfolio Engine — position layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class PositionAtom(Base):
    __tablename__ = "pe_position_atoms"
    __table_args__ = (
        Index("ix_pe_position_atoms_portfolio_id", "portfolio_id"),
        Index("ix_pe_position_atoms_sleeve_id", "sleeve_id"),
        Index("ix_pe_position_atoms_wallet_id", "wallet_id"),
        Index("ix_pe_position_atoms_instrument_id", "instrument_id"),
        Index("ix_pe_position_atoms_strategy_instance_id", "strategy_instance_id"),
        Index("ix_pe_position_atoms_parent_position_id", "parent_position_id"),
        Index("ix_pe_position_atoms_position_type", "position_type"),
        Index("ix_pe_position_atoms_status", "status"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    sleeve_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_sleeves.id", ondelete="SET NULL"),
        nullable=True,
    )
    wallet_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_wallet_containers.id", ondelete="SET NULL"),
        nullable=True,
    )
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_instruments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # TODO: add FK to pe_strategy_instances.id when the strategies module is implemented.
    strategy_instance_id = Column(UUID(as_uuid=True), nullable=True)
    parent_position_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_position_atoms.id", ondelete="SET NULL"),
        nullable=True,
    )

    position_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, server_default="open")

    quantity = Column(Numeric(30, 10), nullable=False, server_default="0")
    available_quantity = Column(Numeric(30, 10), nullable=False, server_default="0")
    locked_quantity = Column(Numeric(30, 10), nullable=False, server_default="0")
    market_value = Column(Numeric(30, 10), nullable=True)
    cost_basis = Column(Numeric(30, 10), nullable=True)
    average_entry_price = Column(Numeric(30, 10), nullable=True)
    accrued_income = Column(Numeric(30, 10), nullable=False, server_default="0")
    unrealized_pnl = Column(Numeric(30, 10), nullable=True)
    realized_pnl = Column(Numeric(30, 10), nullable=False, server_default="0")

    lockup_status = Column(String(30), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", lazy="select")
    sleeve = relationship("Sleeve", lazy="select")
    wallet = relationship("WalletContainer", lazy="select")
    instrument = relationship("Instrument", lazy="select")
    parent_position = relationship("PositionAtom", remote_side="PositionAtom.id", lazy="select")
