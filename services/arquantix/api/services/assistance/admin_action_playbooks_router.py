"""Admin CRUD — catalogue ``assistance_action_playbooks`` (parcours CAL)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import AssistanceActionPlaybook, get_db
from services.assistance.action_playbooks_catalog import (
    invalidate_playbook_cache,
    render_enabled_playbooks_markdown,
)
from services.assistance.agents.orchestration_context import TRANSACTION_KINDS
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

logger = logging.getLogger(__name__)

admin_router = APIRouter(
    prefix="/api/admin/assistance/action-playbooks",
    tags=["assistance-action-playbooks"],
)
_guard = require_admin_or_ops()


class PlaybookRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    action_key: str
    label: str
    description: Optional[str] = None
    transaction_kind: str
    agent_id: str
    definition: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool
    sort_order: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PlaybookListResponse(BaseModel):
    items: list[PlaybookRead]
    total: int
    skip: int
    limit: int


class PlaybookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_key: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    transaction_kind: str = Field(..., min_length=1, max_length=32)
    agent_id: str = Field(default="product", max_length=32)
    definition: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True
    sort_order: int = 0


class PlaybookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    transaction_kind: Optional[str] = Field(default=None, min_length=1, max_length=32)
    agent_id: Optional[str] = Field(default=None, max_length=32)
    definition: Optional[dict[str, Any]] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class PreviewRenderResponse(BaseModel):
    markdown: str
    chars: int


def _serialize(row: AssistanceActionPlaybook) -> PlaybookRead:
    return PlaybookRead(
        id=str(row.id),
        action_key=row.action_key,
        label=row.label,
        description=row.description,
        transaction_kind=row.transaction_kind,
        agent_id=row.agent_id,
        definition=row.definition if isinstance(row.definition, dict) else {},
        is_enabled=bool(row.is_enabled),
        sort_order=int(row.sort_order or 0),
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


def _validate_transaction_kind(kind: str) -> None:
    k = (kind or "").strip().lower()
    if k not in TRANSACTION_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"transaction_kind_invalide:{kind} attendu un de {sorted(TRANSACTION_KINDS)}",
        )


@admin_router.get("/preview-render", response_model=PreviewRenderResponse)
def preview_render(
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
    _: Any = Depends(_guard),
):
    if refresh:
        invalidate_playbook_cache()
    md = render_enabled_playbooks_markdown(db)
    return PreviewRenderResponse(markdown=md, chars=len(md))


@admin_router.get("/", response_model=PlaybookListResponse)
def list_playbooks(
    is_enabled: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Any = Depends(_guard),
):
    q = db.query(AssistanceActionPlaybook)
    if is_enabled is not None:
        q = q.filter(AssistanceActionPlaybook.is_enabled.is_(is_enabled))
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            (AssistanceActionPlaybook.action_key.ilike(s))
            | (AssistanceActionPlaybook.label.ilike(s))
        )
    total = q.count()
    rows = (
        q.order_by(
            AssistanceActionPlaybook.sort_order.asc(),
            AssistanceActionPlaybook.action_key.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return PlaybookListResponse(
        items=[_serialize(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@admin_router.get("/{action_key}", response_model=PlaybookRead)
def get_playbook(
    action_key: str,
    db: Session = Depends(get_db),
    _: Any = Depends(_guard),
):
    row = (
        db.query(AssistanceActionPlaybook)
        .filter(AssistanceActionPlaybook.action_key == action_key)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return _serialize(row)


@admin_router.post("/", response_model=PlaybookRead, status_code=status.HTTP_201_CREATED)
def create_playbook(
    payload: PlaybookCreate,
    db: Session = Depends(get_db),
    _: Any = Depends(_guard),
):
    _validate_transaction_kind(payload.transaction_kind)
    exists = (
        db.query(AssistanceActionPlaybook)
        .filter(AssistanceActionPlaybook.action_key == payload.action_key.strip())
        .one_or_none()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="action_key_exists",
        )
    row = AssistanceActionPlaybook(
        action_key=payload.action_key.strip(),
        label=payload.label.strip(),
        description=(payload.description or "").strip() or None,
        transaction_kind=payload.transaction_kind.strip().lower(),
        agent_id=(payload.agent_id or "product").strip(),
        definition=dict(payload.definition or {}),
        is_enabled=payload.is_enabled,
        sort_order=payload.sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    invalidate_playbook_cache()
    logger.info("admin_action_playbook.create key=%s", row.action_key)
    return _serialize(row)


@admin_router.put("/{action_key}", response_model=PlaybookRead)
def update_playbook(
    action_key: str,
    payload: PlaybookUpdate,
    db: Session = Depends(get_db),
    _: Any = Depends(_guard),
):
    if payload.transaction_kind is not None:
        _validate_transaction_kind(payload.transaction_kind)
    row = (
        db.query(AssistanceActionPlaybook)
        .filter(AssistanceActionPlaybook.action_key == action_key)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")

    if payload.label is not None:
        row.label = payload.label.strip()
    if payload.description is not None:
        row.description = payload.description.strip() or None
    if payload.transaction_kind is not None:
        row.transaction_kind = payload.transaction_kind.strip().lower()
    if payload.agent_id is not None:
        row.agent_id = payload.agent_id.strip()
    if payload.definition is not None:
        row.definition = dict(payload.definition)
    if payload.is_enabled is not None:
        row.is_enabled = payload.is_enabled
    if payload.sort_order is not None:
        row.sort_order = payload.sort_order

    db.commit()
    db.refresh(row)
    invalidate_playbook_cache()
    logger.info("admin_action_playbook.update key=%s", action_key)
    return _serialize(row)


@admin_router.delete("/{action_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playbook(
    action_key: str,
    db: Session = Depends(get_db),
    _: Any = Depends(_guard),
):
    row = (
        db.query(AssistanceActionPlaybook)
        .filter(AssistanceActionPlaybook.action_key == action_key)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    db.delete(row)
    db.commit()
    invalidate_playbook_cache()
    logger.info("admin_action_playbook.delete key=%s", action_key)
    return None
