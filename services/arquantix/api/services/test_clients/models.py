"""SQLAlchemy model for app_runtime_settings (generic key-value runtime config)."""
import uuid

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class AppRuntimeSetting(Base):
    __tablename__ = "app_runtime_settings"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=True)
    metadata_ = Column("metadata_", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
