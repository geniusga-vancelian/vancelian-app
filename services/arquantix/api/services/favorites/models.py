"""ClientFavorite SQLAlchemy model."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base

ALLOWED_ENTITY_TYPES = {"instrument", "exclusive_offer", "bundle"}
MAX_FAVORITES_PER_TYPE = 10


class ClientFavorite(Base):
    __tablename__ = "client_favorites"
    __table_args__ = (
        UniqueConstraint("client_id", "entity_type", "entity_id", name="uq_client_favorites_client_entity"),
        Index("ix_client_favorites_client_type", "client_id", "entity_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("public.pe_clients.id"), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
