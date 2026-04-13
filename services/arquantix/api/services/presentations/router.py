"""Routes FastAPI — présentations, templates, versions."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from services.presentations import service as svc
from services.presentations.schemas import (
    PresentationDeckCreate,
    PresentationDeckOut,
    PresentationDeckSummaryOut,
    PresentationDeckUpdate,
    PresentationSlideCreate,
    PresentationSlideTemplateCreate,
    PresentationSlideTemplateOut,
    PresentationSlideTemplateUpdate,
    PresentationSlideUpdate,
    PresentationVersionCreate,
    PresentationVersionDetailOut,
    PresentationVersionSlideOut,
    PresentationVersionSummaryOut,
    PresentationVersionUpdate,
    SaveDraftBody,
    SlidesReorderBody,
    ValidateSlideBody,
)
from services.presentations.models import PresentationVersionSlide
from services.presentations.validation import SlideContentValidationError


templates_router = APIRouter(prefix="/api/presentation-templates", tags=["presentation-templates"])
presentations_router = APIRouter(prefix="/api/presentations", tags=["presentations"])
version_router = APIRouter(prefix="/api/presentation-versions", tags=["presentation-versions"])


def _http_from_service_error(exc: Exception) -> HTTPException:
    msg = str(exc)
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=msg)
    if isinstance(exc, ValueError):
        if msg.startswith("duplicate_"):
            return HTTPException(status_code=409, detail=msg)
        if "slide_validation" in msg:
            return HTTPException(status_code=422, detail=msg)
        return HTTPException(status_code=400, detail=msg)
    return HTTPException(status_code=500, detail="internal_error")


def _slide_out(s) -> PresentationVersionSlideOut:
    return PresentationVersionSlideOut(
        id=s.id,
        presentation_version_id=s.presentation_version_id,
        sort_order=s.sort_order,
        slide_template_id=s.slide_template_id,
        template_key=s.template.key if s.template else None,
        slide_title=s.slide_title,
        subtitle=s.subtitle,
        content_json=s.content_json,
        style_overrides_json=s.style_overrides_json,
        notes_json=s.notes_json,
        metadata_json=s.metadata_json,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _version_detail(v) -> PresentationVersionDetailOut:
    slides = sorted(v.slides, key=lambda x: x.sort_order)
    return PresentationVersionDetailOut(
        id=v.id,
        presentation_id=v.presentation_id,
        version_number=v.version_number,
        version_label=v.version_label,
        status=v.status,
        is_current=v.is_current,
        changelog=v.changelog,
        validated_at=v.validated_at,
        archived_at=v.archived_at,
        created_at=v.created_at,
        updated_at=v.updated_at,
        snapshot_json=v.snapshot_json if isinstance(v.snapshot_json, dict) else None,
        slides=[_slide_out(s) for s in slides],
    )


# --- Templates ---


@templates_router.get("", response_model=List[PresentationSlideTemplateOut])
def list_presentation_templates(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_templates(db, search=search, category=category, status=status)


@templates_router.post("/validate-content")
def validate_slide_content_against_template(
    body: ValidateSlideBody,
    template_id: uuid.UUID = Query(..., description="UUID du template slide"),
    db: Session = Depends(get_db),
):
    try:
        return svc.validate_slide_payload(db, template_id, body.content_json)
    except LookupError as e:
        raise _http_from_service_error(e) from e
    except SlideContentValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"message": str(e), "errors": e.errors},
        ) from e


@templates_router.get("/{template_id}", response_model=PresentationSlideTemplateOut)
def get_presentation_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    row = svc.get_template(db, template_id)
    if not row:
        raise HTTPException(status_code=404, detail="template_not_found")
    return row


@templates_router.post("", response_model=PresentationSlideTemplateOut)
def post_presentation_template(body: PresentationSlideTemplateCreate, db: Session = Depends(get_db)):
    try:
        return svc.create_template(db, body)
    except ValueError as e:
        raise _http_from_service_error(e) from e


@templates_router.put("/{template_id}", response_model=PresentationSlideTemplateOut)
def put_presentation_template(
    template_id: uuid.UUID, body: PresentationSlideTemplateUpdate, db: Session = Depends(get_db)
):
    try:
        return svc.update_template(db, template_id, body)
    except LookupError as e:
        raise _http_from_service_error(e) from e


@templates_router.post("/{template_id}/archive", response_model=PresentationSlideTemplateOut)
def archive_presentation_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return svc.archive_template(db, template_id)
    except LookupError as e:
        raise _http_from_service_error(e) from e


@templates_router.post("/{template_id}/restore", response_model=PresentationSlideTemplateOut)
def restore_presentation_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return svc.restore_template(db, template_id)
    except LookupError as e:
        raise _http_from_service_error(e) from e


# --- Decks ---


@presentations_router.get("", response_model=List[PresentationDeckSummaryOut])
def list_presentations(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
):
    return svc.list_decks(db, include_archived=include_archived)


@presentations_router.get("/{presentation_id}", response_model=PresentationDeckOut)
def get_presentation(presentation_id: uuid.UUID, db: Session = Depends(get_db)):
    deck = svc.get_deck(db, presentation_id)
    if not deck:
        raise HTTPException(status_code=404, detail="deck_not_found")
    return deck


@presentations_router.post("", response_model=PresentationDeckOut)
def post_presentation(body: PresentationDeckCreate, db: Session = Depends(get_db)):
    try:
        return svc.create_deck(db, body)
    except ValueError as e:
        raise _http_from_service_error(e) from e


@presentations_router.put("/{presentation_id}", response_model=PresentationDeckOut)
def put_presentation(
    presentation_id: uuid.UUID, body: PresentationDeckUpdate, db: Session = Depends(get_db)
):
    try:
        return svc.update_deck(db, presentation_id, body)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@presentations_router.post("/{presentation_id}/archive", response_model=PresentationDeckOut)
def archive_presentation(presentation_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return svc.archive_deck(db, presentation_id)
    except LookupError as e:
        raise _http_from_service_error(e) from e


@presentations_router.post("/{presentation_id}/restore", response_model=PresentationDeckOut)
def restore_presentation(presentation_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return svc.restore_deck(db, presentation_id)
    except LookupError as e:
        raise _http_from_service_error(e) from e


@presentations_router.get("/{presentation_id}/versions", response_model=List[PresentationVersionSummaryOut])
def list_presentation_versions(presentation_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.get_deck(db, presentation_id):
        raise HTTPException(status_code=404, detail="deck_not_found")
    return svc.list_versions(db, presentation_id)


@presentations_router.post("/{presentation_id}/versions", response_model=PresentationVersionDetailOut)
def post_presentation_version(
    presentation_id: uuid.UUID, body: PresentationVersionCreate, db: Session = Depends(get_db)
):
    try:
        v = svc.create_version(db, presentation_id, body)
        return _version_detail(v)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


# --- Versions (by id) ---


@version_router.get("/{version_id}", response_model=PresentationVersionDetailOut)
def get_presentation_version(version_id: uuid.UUID, db: Session = Depends(get_db)):
    v = svc.get_version(db, version_id)
    if not v:
        raise HTTPException(status_code=404, detail="version_not_found")
    return _version_detail(v)


@version_router.put("/{version_id}", response_model=PresentationVersionDetailOut)
def put_presentation_version(
    version_id: uuid.UUID, body: PresentationVersionUpdate, db: Session = Depends(get_db)
):
    try:
        v = svc.update_version(db, version_id, body)
        return _version_detail(v)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/validate", response_model=PresentationVersionDetailOut)
def validate_presentation_version(version_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        v = svc.validate_version(db, version_id)
        return _version_detail(v)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/archive", response_model=PresentationVersionDetailOut)
def archive_presentation_version(version_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        v = svc.archive_version(db, version_id)
        return _version_detail(v)
    except LookupError as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/restore", response_model=PresentationVersionDetailOut)
def restore_presentation_version(version_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        v = svc.restore_version(db, version_id)
        return _version_detail(v)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/duplicate", response_model=PresentationVersionDetailOut)
def duplicate_presentation_version(version_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        v = svc.duplicate_version(db, version_id)
        return _version_detail(v)
    except LookupError as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/set-current", response_model=PresentationVersionDetailOut)
def set_current_presentation_version(version_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        v = svc.set_current_version(db, version_id)
        return _version_detail(v)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/save-draft", response_model=PresentationVersionDetailOut)
def save_draft_presentation_version(
    version_id: uuid.UUID,
    body: Optional[SaveDraftBody] = Body(default=None),
    db: Session = Depends(get_db),
):
    try:
        v = svc.save_draft(db, version_id, body)
        return _version_detail(v)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/slides/reorder", response_model=PresentationVersionDetailOut)
def reorder_presentation_slides(
    version_id: uuid.UUID, body: SlidesReorderBody, db: Session = Depends(get_db)
):
    try:
        v = svc.reorder_slides(db, version_id, body.slide_ids)
        return _version_detail(v)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.post("/{version_id}/slides", response_model=PresentationVersionSlideOut)
def post_presentation_slide(
    version_id: uuid.UUID, body: PresentationSlideCreate, db: Session = Depends(get_db)
):
    try:
        s = svc.create_slide(db, version_id, body)
        row = (
            db.query(PresentationVersionSlide)
            .options(joinedload(PresentationVersionSlide.template))
            .filter(PresentationVersionSlide.id == s.id)
            .first()
        )
        assert row
        return _slide_out(row)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.put("/{version_id}/slides/{slide_id}", response_model=PresentationVersionSlideOut)
def put_presentation_slide(
    version_id: uuid.UUID, slide_id: uuid.UUID, body: PresentationSlideUpdate, db: Session = Depends(get_db)
):
    try:
        svc.update_slide(db, version_id, slide_id, body)
        row = (
            db.query(PresentationVersionSlide)
            .options(joinedload(PresentationVersionSlide.template))
            .filter(
                PresentationVersionSlide.id == slide_id,
                PresentationVersionSlide.presentation_version_id == version_id,
            )
            .first()
        )
        assert row
        return _slide_out(row)
    except (LookupError, ValueError) as e:
        raise _http_from_service_error(e) from e


@version_router.delete("/{version_id}/slides/{slide_id}", status_code=204)
def delete_presentation_slide(version_id: uuid.UUID, slide_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        svc.delete_slide(db, version_id, slide_id)
    except LookupError as e:
        raise _http_from_service_error(e) from e
    except ValueError as e:
        raise _http_from_service_error(e) from e
