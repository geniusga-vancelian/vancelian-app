"""Logique métier — decks, versions, templates, slides."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from services.presentations.models import (
    PresentationDeck,
    PresentationDeckVersion,
    PresentationSlideTemplate,
    PresentationVersionSlide,
)
from services.presentations.schemas import (
    PresentationDeckCreate,
    PresentationDeckUpdate,
    PresentationSlideCreate,
    PresentationSlideTemplateCreate,
    PresentationSlideTemplateUpdate,
    PresentationSlideUpdate,
    PresentationVersionCreate,
    PresentationVersionUpdate,
    SaveDraftBody,
    SaveDraftSlidePayload,
)
from services.presentations.validation import SlideContentValidationError, validate_content_against_schema


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Templates ---


def list_templates(
    db: Session,
    *,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> List[PresentationSlideTemplate]:
    q = db.query(PresentationSlideTemplate)
    if category:
        q = q.filter(PresentationSlideTemplate.category == category)
    if status:
        q = q.filter(PresentationSlideTemplate.status == status)
    if search:
        term = f"%{search}%"
        q = q.filter(
            (PresentationSlideTemplate.name.ilike(term))
            | (PresentationSlideTemplate.key.ilike(term))
            | (PresentationSlideTemplate.description.ilike(term))
        )
    return q.order_by(PresentationSlideTemplate.category, PresentationSlideTemplate.key).all()


def get_template(db: Session, tid: uuid.UUID) -> Optional[PresentationSlideTemplate]:
    return db.query(PresentationSlideTemplate).filter(PresentationSlideTemplate.id == tid).first()


def get_template_by_key(db: Session, key: str) -> Optional[PresentationSlideTemplate]:
    return db.query(PresentationSlideTemplate).filter(PresentationSlideTemplate.key == key).first()


def create_template(db: Session, body: PresentationSlideTemplateCreate) -> PresentationSlideTemplate:
    if get_template_by_key(db, body.key):
        raise ValueError("duplicate_template_key")
    row = PresentationSlideTemplate(
        key=body.key.strip(),
        name=body.name,
        category=body.category,
        description=body.description,
        status=body.status,
        preview_image_url=body.preview_image_url,
        schema_json=body.schema_json,
        default_content_json=body.default_content_json or {},
        design_tokens_json=body.design_tokens_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_template(db: Session, tid: uuid.UUID, body: PresentationSlideTemplateUpdate) -> PresentationSlideTemplate:
    row = get_template(db, tid)
    if not row:
        raise LookupError("template_not_found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def archive_template(db: Session, tid: uuid.UUID) -> PresentationSlideTemplate:
    row = get_template(db, tid)
    if not row:
        raise LookupError("template_not_found")
    row.status = "archived"
    db.commit()
    db.refresh(row)
    return row


def restore_template(db: Session, tid: uuid.UUID) -> PresentationSlideTemplate:
    row = get_template(db, tid)
    if not row:
        raise LookupError("template_not_found")
    row.status = "active"
    db.commit()
    db.refresh(row)
    return row


# --- Decks ---


def list_decks(db: Session, *, include_archived: bool = False) -> List[PresentationDeck]:
    q = db.query(PresentationDeck)
    if not include_archived:
        q = q.filter(PresentationDeck.archived_at.is_(None))
    return q.order_by(PresentationDeck.updated_at.desc()).all()


def get_deck(db: Session, did: uuid.UUID) -> Optional[PresentationDeck]:
    return db.query(PresentationDeck).filter(PresentationDeck.id == did).first()


def get_deck_by_slug(db: Session, slug: str) -> Optional[PresentationDeck]:
    return db.query(PresentationDeck).filter(PresentationDeck.slug == slug).first()


def create_deck(db: Session, body: PresentationDeckCreate) -> PresentationDeck:
    if get_deck_by_slug(db, body.slug.strip()):
        raise ValueError("duplicate_slug")
    deck = PresentationDeck(
        name=body.name,
        slug=body.slug.strip(),
        description=body.description,
        deck_type=body.deck_type,
    )
    db.add(deck)
    db.flush()
    if body.create_initial_version:
        v = PresentationDeckVersion(
            presentation_id=deck.id,
            version_number=1,
            version_label="V1",
            status="draft",
            is_current=True,
        )
        db.add(v)
        db.flush()
        deck.current_version_id = v.id
    db.commit()
    db.refresh(deck)
    return deck


def update_deck(db: Session, did: uuid.UUID, body: PresentationDeckUpdate) -> PresentationDeck:
    deck = get_deck(db, did)
    if not deck:
        raise LookupError("deck_not_found")
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        other = get_deck_by_slug(db, data["slug"].strip())
        if other and other.id != deck.id:
            raise ValueError("duplicate_slug")
        data["slug"] = data["slug"].strip()
    for k, v in data.items():
        setattr(deck, k, v)
    db.commit()
    db.refresh(deck)
    return deck


def archive_deck(db: Session, did: uuid.UUID) -> PresentationDeck:
    deck = get_deck(db, did)
    if not deck:
        raise LookupError("deck_not_found")
    deck.archived_at = _utcnow()
    db.commit()
    db.refresh(deck)
    return deck


def restore_deck(db: Session, did: uuid.UUID) -> PresentationDeck:
    deck = get_deck(db, did)
    if not deck:
        raise LookupError("deck_not_found")
    deck.archived_at = None
    db.commit()
    db.refresh(deck)
    return deck


# --- Versions ---


def get_version(db: Session, vid: uuid.UUID) -> Optional[PresentationDeckVersion]:
    return (
        db.query(PresentationDeckVersion)
        .options(
            joinedload(PresentationDeckVersion.slides).joinedload(PresentationVersionSlide.template),
        )
        .filter(PresentationDeckVersion.id == vid)
        .first()
    )


def list_versions(db: Session, deck_id: uuid.UUID) -> List[PresentationDeckVersion]:
    return (
        db.query(PresentationDeckVersion)
        .filter(PresentationDeckVersion.presentation_id == deck_id)
        .order_by(PresentationDeckVersion.version_number.desc())
        .all()
    )


def _next_version_number(db: Session, deck_id: uuid.UUID) -> int:
    m = db.query(func.max(PresentationDeckVersion.version_number)).filter(
        PresentationDeckVersion.presentation_id == deck_id
    ).scalar()
    return (m or 0) + 1


def _clear_current_flags(db: Session, deck_id: uuid.UUID) -> None:
    db.query(PresentationDeckVersion).filter(
        PresentationDeckVersion.presentation_id == deck_id,
        PresentationDeckVersion.is_current.is_(True),
    ).update({"is_current": False})


def create_version(db: Session, deck_id: uuid.UUID, body: PresentationVersionCreate) -> PresentationDeckVersion:
    deck = get_deck(db, deck_id)
    if not deck:
        raise LookupError("deck_not_found")
    if deck.archived_at is not None:
        raise ValueError("deck_archived")

    num = _next_version_number(db, deck_id)
    label = body.version_label or f"V{num}"
    v = PresentationDeckVersion(
        presentation_id=deck_id,
        version_number=num,
        version_label=label,
        status="draft",
        is_current=False,
        changelog=body.changelog,
    )
    db.add(v)
    db.flush()

    if body.copy_from_version_id:
        src = get_version(db, body.copy_from_version_id)
        if not src or src.presentation_id != deck_id:
            raise ValueError("invalid_copy_source")
        slides = sorted(src.slides, key=lambda s: s.sort_order)
        for s in slides:
            db.add(
                PresentationVersionSlide(
                    presentation_version_id=v.id,
                    sort_order=s.sort_order,
                    slide_template_id=s.slide_template_id,
                    slide_title=s.slide_title,
                    subtitle=s.subtitle,
                    content_json=s.content_json,
                    style_overrides_json=s.style_overrides_json,
                    notes_json=s.notes_json,
                    metadata_json=s.metadata_json,
                )
            )
    db.commit()
    db.refresh(v)
    return get_version(db, v.id)  # type: ignore


def update_version(db: Session, vid: uuid.UUID, body: PresentationVersionUpdate) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "draft":
        raise ValueError("version_not_mutable")
    data = body.model_dump(exclude_unset=True)
    for k, val in data.items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return get_version(db, v.id)  # type: ignore


def _build_snapshot_document(v: PresentationDeckVersion) -> dict[str, Any]:
    slides_sorted = sorted(v.slides, key=lambda s: s.sort_order)
    blocks: List[dict[str, Any]] = []
    for s in slides_sorted:
        tmpl = s.template
        blocks.append(
            {
                "id": str(s.id),
                "sort_order": s.sort_order,
                "template_id": str(s.slide_template_id),
                "template_key": tmpl.key if tmpl else None,
                "slide_title": s.slide_title,
                "subtitle": s.subtitle,
                "content_json": s.content_json or {},
                "style_overrides_json": s.style_overrides_json,
                "notes_json": s.notes_json,
                "metadata_json": s.metadata_json,
            }
        )
    return {
        "version_id": str(v.id),
        "version_number": v.version_number,
        "version_label": v.version_label,
        "presentation_id": str(v.presentation_id),
        "captured_at": _utcnow().isoformat(),
        "slides": blocks,
    }


def validate_version(db: Session, vid: uuid.UUID) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "draft":
        raise ValueError("only_draft_can_validate")
    for s in v.slides:
        tmpl = get_template(db, s.slide_template_id)
        if tmpl:
            try:
                validate_content_against_schema(
                    tmpl.schema_json if isinstance(tmpl.schema_json, dict) else None,
                    s.content_json if isinstance(s.content_json, dict) else {},
                )
            except SlideContentValidationError as e:
                raise ValueError(f"slide_validation:{s.id}:{e}") from e
    v.snapshot_json = _build_snapshot_document(v)
    v.status = "validated"
    v.validated_at = _utcnow()
    db.commit()
    db.refresh(v)
    return get_version(db, v.id)  # type: ignore


def archive_version(db: Session, vid: uuid.UUID) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    v.status = "archived"
    v.archived_at = _utcnow()
    if v.is_current:
        v.is_current = False
        deck = get_deck(db, v.presentation_id)
        if deck and deck.current_version_id == v.id:
            deck.current_version_id = None
    db.commit()
    db.refresh(v)
    return get_version(db, v.id)  # type: ignore


def restore_version(db: Session, vid: uuid.UUID) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "archived":
        raise ValueError("not_archived")
    v.status = "draft"
    v.archived_at = None
    db.commit()
    db.refresh(v)
    return get_version(db, v.id)  # type: ignore


def duplicate_version(db: Session, vid: uuid.UUID) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    return create_version(
        db,
        v.presentation_id,
        PresentationVersionCreate(copy_from_version_id=v.id, version_label=None, changelog=None),
    )


def set_current_version(db: Session, vid: uuid.UUID) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status == "archived":
        raise ValueError("archived_cannot_be_current")
    _clear_current_flags(db, v.presentation_id)
    v.is_current = True
    deck = get_deck(db, v.presentation_id)
    if deck:
        deck.current_version_id = v.id
    db.commit()
    db.refresh(v)
    return get_version(db, v.id)  # type: ignore


def save_draft(db: Session, vid: uuid.UUID, body: Optional[SaveDraftBody] = None) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "draft":
        raise ValueError("only_draft_save")
    if body and body.changelog is not None:
        v.changelog = body.changelog
    if body and body.slides is not None:
        db.query(PresentationVersionSlide).filter(
            PresentationVersionSlide.presentation_version_id == v.id
        ).delete(synchronize_session=False)
        for item in body.slides:
            tmpl = get_template(db, item.slide_template_id)
            if not tmpl:
                raise ValueError("template_not_found")
            try:
                validate_content_against_schema(
                    tmpl.schema_json if isinstance(tmpl.schema_json, dict) else None,
                    item.content_json if isinstance(item.content_json, dict) else {},
                )
            except SlideContentValidationError as e:
                raise ValueError(f"slide_validation:batch:{e}") from e
            db.add(
                PresentationVersionSlide(
                    presentation_version_id=v.id,
                    sort_order=item.sort_order,
                    slide_template_id=item.slide_template_id,
                    slide_title=item.slide_title,
                    subtitle=item.subtitle,
                    content_json=item.content_json or {},
                    style_overrides_json=item.style_overrides_json,
                    notes_json=item.notes_json,
                    metadata_json=item.metadata_json,
                )
            )
    v.updated_at = _utcnow()
    db.commit()
    db.refresh(v)
    return get_version(db, v.id)  # type: ignore


def reorder_slides(db: Session, vid: uuid.UUID, slide_ids: Sequence[uuid.UUID]) -> PresentationDeckVersion:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "draft":
        raise ValueError("only_draft_mutate_slides")
    by_id = {s.id: s for s in v.slides}
    if set(slide_ids) != set(by_id.keys()):
        raise ValueError("slide_set_mismatch")
    for i, sid in enumerate(slide_ids):
        by_id[sid].sort_order = i
    v.updated_at = _utcnow()
    db.commit()
    return get_version(db, v.id)  # type: ignore


def create_slide(db: Session, vid: uuid.UUID, body: PresentationSlideCreate) -> PresentationVersionSlide:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "draft":
        raise ValueError("only_draft_mutate_slides")
    tmpl = get_template(db, body.slide_template_id)
    if not tmpl:
        raise LookupError("template_not_found")
    content = body.content_json
    if content is None and tmpl.default_content_json:
        content = tmpl.default_content_json if isinstance(tmpl.default_content_json, dict) else {}
    if content is None:
        content = {}
    try:
        validate_content_against_schema(
            tmpl.schema_json if isinstance(tmpl.schema_json, dict) else None,
            content,
        )
    except SlideContentValidationError as e:
        raise ValueError(f"slide_validation:{e}") from e
    max_ord = db.query(func.max(PresentationVersionSlide.sort_order)).filter(
        PresentationVersionSlide.presentation_version_id == v.id
    ).scalar()
    next_ord = (max_ord if max_ord is not None else -1) + 1
    sort_order = body.sort_order if body.sort_order is not None else next_ord
    row = PresentationVersionSlide(
        presentation_version_id=v.id,
        sort_order=sort_order,
        slide_template_id=body.slide_template_id,
        slide_title=body.slide_title,
        subtitle=body.subtitle,
        content_json=content,
        style_overrides_json=body.style_overrides_json,
        notes_json=body.notes_json,
        metadata_json=body.metadata_json,
    )
    db.add(row)
    v.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def update_slide(db: Session, vid: uuid.UUID, slide_id: uuid.UUID, body: PresentationSlideUpdate) -> PresentationVersionSlide:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "draft":
        raise ValueError("only_draft_mutate_slides")
    row = (
        db.query(PresentationVersionSlide)
        .filter(
            PresentationVersionSlide.id == slide_id,
            PresentationVersionSlide.presentation_version_id == v.id,
        )
        .first()
    )
    if not row:
        raise LookupError("slide_not_found")
    tmpl = get_template(db, row.slide_template_id)
    data = body.model_dump(exclude_unset=True)
    if "content_json" in data:
        content = data["content_json"]
        try:
            validate_content_against_schema(
                tmpl.schema_json if tmpl and isinstance(tmpl.schema_json, dict) else None,
                content if isinstance(content, dict) else {},
            )
        except SlideContentValidationError as e:
            raise ValueError(f"slide_validation:{e}") from e
    for k, val in data.items():
        setattr(row, k, val)
    v.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_slide(db: Session, vid: uuid.UUID, slide_id: uuid.UUID) -> None:
    v = get_version(db, vid)
    if not v:
        raise LookupError("version_not_found")
    if v.status != "draft":
        raise ValueError("only_draft_mutate_slides")
    row = (
        db.query(PresentationVersionSlide)
        .filter(
            PresentationVersionSlide.id == slide_id,
            PresentationVersionSlide.presentation_version_id == v.id,
        )
        .first()
    )
    if not row:
        raise LookupError("slide_not_found")
    db.delete(row)
    v.updated_at = _utcnow()
    db.commit()


def validate_slide_payload(
    db: Session,
    template_id: uuid.UUID,
    content_json: dict[str, Any],
) -> dict[str, Any]:
    tmpl = get_template(db, template_id)
    if not tmpl:
        raise LookupError("template_not_found")
    validate_content_against_schema(
        tmpl.schema_json if isinstance(tmpl.schema_json, dict) else None,
        content_json,
    )
    return {"ok": True, "template_key": tmpl.key}
