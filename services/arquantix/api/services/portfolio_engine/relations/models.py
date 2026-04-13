"""SQLAlchemy model for the pe_position_relations table (Portfolio Engine — relation layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, String, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class PositionRelation(Base):
    __tablename__ = "pe_position_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_position_id", "target_position_id", "relation_type",
            name="uq_pe_position_relations_src_tgt_type",
        ),
        Index("ix_pe_position_relations_source", "source_position_id"),
        Index("ix_pe_position_relations_target", "target_position_id"),
        Index("ix_pe_position_relations_type", "relation_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    source_position_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_position_atoms.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_position_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_position_atoms.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type = Column(String(50), nullable=False)
    parameters = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_position = relationship(
        "PositionAtom", foreign_keys=[source_position_id], lazy="select",
    )
    target_position = relationship(
        "PositionAtom", foreign_keys=[target_position_id], lazy="select",
    )
