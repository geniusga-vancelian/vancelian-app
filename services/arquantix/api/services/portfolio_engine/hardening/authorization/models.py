"""SQLAlchemy model for pe_advisor_client_assignments (Authorization Scoping)."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class AdvisorClientAssignment(Base):
    __tablename__ = "pe_advisor_client_assignments"
    __table_args__ = (
        UniqueConstraint("advisor_actor_id", "client_id", name="uq_advisor_client"),
        Index("ix_pe_advisor_assign_advisor", "advisor_actor_id"),
        Index("ix_pe_advisor_assign_client", "client_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    advisor_actor_id = Column(String(255), nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, server_default="active")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
