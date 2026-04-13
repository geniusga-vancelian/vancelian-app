"""SQLAlchemy model for the pe_product_definitions table (Portfolio Engine — catalog layer)."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class ProductDefinition(Base):
    __tablename__ = "pe_product_definitions"
    __table_args__ = (
        Index("ix_pe_product_definitions_product_type", "product_type"),
        Index("ix_pe_product_definitions_status", "status"),
        Index("ix_pe_product_definitions_metadata", "metadata", postgresql_using="gin"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    product_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    product_type = Column(String(50), nullable=False)
    risk_label = Column(String(30), nullable=True)
    base_currency = Column(String(20), nullable=False, server_default="EUR")
    is_public = Column(Boolean, nullable=False, server_default="false")
    status = Column(String(30), nullable=False, server_default="draft")
    metadata_ = Column("metadata", JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
