"""Schémas Pydantic — API présentations / templates."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Templates ---


class PresentationSlideTemplateCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
    name: str
    category: str = "general"
    description: Optional[str] = None
    status: str = "active"
    preview_image_url: Optional[str] = None
    schema_json: Optional[dict[str, Any]] = None
    default_content_json: Optional[dict[str, Any]] = None
    design_tokens_json: Optional[dict[str, Any]] = None


class PresentationSlideTemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    preview_image_url: Optional[str] = None
    schema_json: Optional[dict[str, Any]] = None
    default_content_json: Optional[dict[str, Any]] = None
    design_tokens_json: Optional[dict[str, Any]] = None


class PresentationSlideTemplateOut(BaseModel):
    id: UUID
    key: str
    name: str
    category: str
    description: Optional[str]
    status: str
    preview_image_url: Optional[str]
    schema_json: Optional[dict[str, Any]]
    default_content_json: Optional[dict[str, Any]]
    design_tokens_json: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Decks ---


class PresentationDeckCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    deck_type: Optional[str] = None
    create_initial_version: bool = True


class PresentationDeckUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    deck_type: Optional[str] = None


class PresentationDeckSummaryOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    deck_type: Optional[str]
    current_version_id: Optional[UUID]
    archived_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PresentationDeckOut(PresentationDeckSummaryOut):
    pass


# --- Versions ---


class PresentationVersionCreate(BaseModel):
    """Nouvelle version ; copie optionnelle depuis une version existante du même deck."""

    copy_from_version_id: Optional[UUID] = None
    version_label: Optional[str] = None
    changelog: Optional[str] = None


class PresentationVersionUpdate(BaseModel):
    version_label: Optional[str] = None
    changelog: Optional[str] = None


class PresentationVersionSummaryOut(BaseModel):
    id: UUID
    presentation_id: UUID
    version_number: int
    version_label: str
    status: str
    is_current: bool
    changelog: Optional[str]
    validated_at: Optional[datetime]
    archived_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PresentationVersionSlideOut(BaseModel):
    id: UUID
    presentation_version_id: UUID
    sort_order: int
    slide_template_id: UUID
    template_key: Optional[str] = None
    slide_title: Optional[str]
    subtitle: Optional[str]
    content_json: Optional[dict[str, Any]]
    style_overrides_json: Optional[dict[str, Any]]
    notes_json: Optional[dict[str, Any]]
    metadata_json: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PresentationVersionDetailOut(PresentationVersionSummaryOut):
    snapshot_json: Optional[dict[str, Any]]
    slides: List[PresentationVersionSlideOut] = []


# --- Slides ---


class PresentationSlideCreate(BaseModel):
    slide_template_id: UUID
    sort_order: Optional[int] = None
    slide_title: Optional[str] = None
    subtitle: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    style_overrides_json: Optional[dict[str, Any]] = None
    notes_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None


class PresentationSlideUpdate(BaseModel):
    sort_order: Optional[int] = None
    slide_title: Optional[str] = None
    subtitle: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    style_overrides_json: Optional[dict[str, Any]] = None
    notes_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None


class SlidesReorderBody(BaseModel):
    slide_ids: List[UUID]


class SaveDraftSlidePayload(BaseModel):
    """Une slide dans un save-draft complet (remplace les lignes existantes si fourni)."""

    slide_template_id: UUID
    sort_order: int = 0
    slide_title: Optional[str] = None
    subtitle: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    style_overrides_json: Optional[dict[str, Any]] = None
    notes_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None


class SaveDraftBody(BaseModel):
    slides: Optional[List[SaveDraftSlidePayload]] = None
    changelog: Optional[str] = None


class ValidateSlideBody(BaseModel):
    content_json: dict[str, Any] = Field(default_factory=dict)
