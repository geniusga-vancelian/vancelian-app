"""SQLAlchemy model for the pe_clients table (Portfolio Engine — ownership layer)."""
import uuid

from sqlalchemy import Column, ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
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

    person = relationship(
        "Person",
        back_populates="trading_client",
        uselist=False,
        foreign_keys=[person_id],
    )
