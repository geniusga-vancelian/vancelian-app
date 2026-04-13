"""
SQLAlchemy models — présentations (decks), versions, templates de slides.

Imported from database.py to register mappers with Base.metadata (Alembic).
"""
import uuid

from sqlalchemy import (
    Column,
    Text,
    DateTime,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class PresentationSlideTemplate(Base):
    __tablename__ = "presentation_slide_templates"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False, server_default="general")
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, server_default="active")
    preview_image_url = Column(Text, nullable=True)
    schema_json = Column(JSONB(astext_type=Text), nullable=True)
    default_content_json = Column(JSONB(astext_type=Text), nullable=True)
    design_tokens_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PresentationDeck(Base):
    __tablename__ = "presentation_decks"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    deck_type = Column(Text, nullable=True)
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.presentation_deck_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)

    versions = relationship(
        "PresentationDeckVersion",
        back_populates="deck",
        foreign_keys="PresentationDeckVersion.presentation_id",
        order_by="PresentationDeckVersion.version_number",
    )
    current_version = relationship(
        "PresentationDeckVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )


class PresentationDeckVersion(Base):
    __tablename__ = "presentation_deck_versions"
    __table_args__ = (
        UniqueConstraint("presentation_id", "version_number", name="uq_presentation_deck_version_num"),
        Index(
            "uq_presentation_deck_one_current",
            "presentation_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.presentation_decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    version_label = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="draft")
    is_current = Column(Boolean, nullable=False, server_default="false")
    changelog = Column(Text, nullable=True)
    snapshot_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    validated_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    deck = relationship(
        "PresentationDeck",
        back_populates="versions",
        foreign_keys=[presentation_id],
    )
    slides = relationship(
        "PresentationVersionSlide",
        back_populates="version",
        order_by="PresentationVersionSlide.sort_order",
        cascade="all, delete-orphan",
    )


class PresentationVersionSlide(Base):
    __tablename__ = "presentation_version_slides"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.presentation_deck_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order = Column(Integer, nullable=False, server_default="0")
    slide_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.presentation_slide_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    slide_title = Column(Text, nullable=True)
    subtitle = Column(Text, nullable=True)
    content_json = Column(JSONB(astext_type=Text), nullable=True)
    style_overrides_json = Column(JSONB(astext_type=Text), nullable=True)
    notes_json = Column(JSONB(astext_type=Text), nullable=True)
    metadata_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    version = relationship("PresentationDeckVersion", back_populates="slides")
    template = relationship("PresentationSlideTemplate")
