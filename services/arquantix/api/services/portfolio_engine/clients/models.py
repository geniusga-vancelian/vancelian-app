"""SQLAlchemy model for the pe_clients table (Portfolio Engine — ownership layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Client(Base):
    __tablename__ = "pe_clients"
    __table_args__ = (
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    # Nullable (PR4) — person_id est la clé métier ; unique partiel sur email non NULL.
    email = Column(String(255), nullable=True, index=True)
    status = Column(String(30), nullable=False, server_default="pending")
    kyc_status = Column(String(30), nullable=False, server_default="not_started")
    reference_currency = Column(String(3), nullable=False, server_default="EUR")
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id"),
        unique=True,
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # ── Palier 2 D.2.3 — Mémoire long-terme cross-conversations (migration 146)
    # Agrégat des faits extraits de toutes les conversations d'assistance du
    # client. Format : `{ "facts": [...], "updated_at": "..." }`. Maintenu
    # par services.assistance.memory.consolidate_conversation et réinjecté
    # dans le system prompt à chaque tour pour offrir une vraie continuité
    # d'expérience cross-conv.
    assistance_long_memory = Column(
        JSONB(astext_type=Text), nullable=False, server_default="{}"
    )

    person = relationship(
        "Person",
        back_populates="trading_client",
        uselist=False,
        foreign_keys=[person_id],
    )
