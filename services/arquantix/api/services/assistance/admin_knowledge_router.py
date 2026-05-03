"""Router admin pour la gestion CRUD de ``product_knowledge``.

Surface HTTP exposée à l'espace admin web (Next.js) sous le préfixe
``/api/admin/assistance/knowledge`` :

  - ``GET    /``                   → liste paginée + filtres + total
  - ``GET    /summary``            → compteurs par topic (pour widgets)
  - ``GET    /preview-block``      → rendu Markdown courant du builder
                                     (tel que les agents le verront)
  - ``GET    /{slug}``             → détail d'une fiche (inclut inactives)
  - ``POST   /``                   → créer une fiche
  - ``PUT    /{slug}``             → mettre à jour (champs partiels)
  - ``DELETE /{slug}``             → supprimer définitivement (rare,
                                     préférer ``is_active=false``)

Garanties :

  - **Auth** : ``require_admin_or_ops()`` (rôle ``admin`` ou ``ops``).
  - **Cache catalogue** : à chaque write réussie (commit OK), le cache
    in-memory du builder est invalidé (``catalog_context_builder.invalidate_cache``).
    Les agents reçoivent donc un bloc à jour dès le tour suivant.
  - **Best-effort log** : toute mutation est loggée avec l'``actor_id``
    pour audit léger (pas un audit_event SOC pour l'instant).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from services.assistance.agents.repositories import product_repo
from services.assistance.agents.runtime.catalog_context_builder import (
    build_catalog_context_block,
    invalidate_cache as invalidate_catalog_cache,
)
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

logger = logging.getLogger(__name__)


admin_router = APIRouter(
    prefix="/api/admin/assistance/knowledge",
    tags=["assistance-knowledge"],
)
_guard = require_admin_or_ops()


# ─── Schemas ────────────────────────────────────────────────────────────────


class KnowledgeRead(BaseModel):
    """Représentation admin d'une row ``product_knowledge``."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    topic: str
    title: str
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeRead]
    total: int
    skip: int
    limit: int


class KnowledgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=1, max_length=80)
    topic: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class KnowledgeUpdate(BaseModel):
    """Update partiel — seuls les champs fournis sont modifiés."""

    model_config = ConfigDict(extra="forbid")

    topic: Optional[str] = Field(default=None, min_length=1, max_length=40)
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    body: Optional[str] = Field(default=None, min_length=1)
    metadata: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class TopicSummary(BaseModel):
    topic: str
    active: int
    inactive: int


class KnowledgeSummaryResponse(BaseModel):
    by_topic: list[TopicSummary]
    allowed_topics: list[str]


class CatalogPreviewResponse(BaseModel):
    block: Optional[str] = None
    chars: int
    lines: int
    is_empty: bool


# ─── Helpers ────────────────────────────────────────────────────────────────


def _safe_invalidate_catalog_cache(actor: ActorContext) -> None:
    """Best-effort : on ne casse jamais une mutation pour un cache."""
    try:
        invalidate_catalog_cache()
    except Exception:  # noqa: BLE001
        logger.warning(
            "admin_knowledge.cache_invalidate_failed actor=%s",
            getattr(actor, "actor_id", "?"),
            exc_info=True,
        )


def _log_mutation(action: str, slug: str, actor: ActorContext) -> None:
    """Audit léger des mutations admin — visible en logs container."""
    logger.info(
        "admin_knowledge.%s slug=%s actor_type=%s actor_id=%s roles=%s",
        action,
        slug,
        getattr(actor, "actor_type", "?"),
        getattr(actor, "actor_id", "?"),
        ",".join(getattr(actor, "roles", [])) or "-",
    )


# ─── Endpoints ─────────────────────────────────────────────────────────────


@admin_router.get("/summary", response_model=KnowledgeSummaryResponse)
def get_summary(
    db: Session = Depends(get_db),
    _: ActorContext = Depends(_guard),
):
    """Compteurs par topic (active / inactive) pour les widgets admin."""
    raw = product_repo.admin_count_by_topic(db)
    by_topic = [
        TopicSummary(topic=t, active=v.get("active", 0), inactive=v.get("inactive", 0))
        for t, v in sorted(raw.items())
    ]
    return KnowledgeSummaryResponse(
        by_topic=by_topic,
        allowed_topics=sorted(product_repo.ALLOWED_TOPICS),
    )


@admin_router.get("/preview-block", response_model=CatalogPreviewResponse)
def preview_block(
    refresh: bool = Query(False, description="Force-invalide le cache avant rendu."),
    db: Session = Depends(get_db),
    _: ActorContext = Depends(_guard),
):
    """Renvoie le bloc-catalogue tel qu'il sera injecté aux agents.

    Utile pour vérifier visuellement avant de publier un changement.
    Avec ``refresh=true``, le cache 60 s est invalidé d'abord pour voir
    le rendu reflétant l'état DB courant immédiatement.
    """
    if refresh:
        invalidate_catalog_cache()
    block = build_catalog_context_block(db)
    return CatalogPreviewResponse(
        block=block,
        chars=len(block) if block else 0,
        lines=len(block.splitlines()) if block else 0,
        is_empty=block is None,
    )


@admin_router.get("/", response_model=KnowledgeListResponse)
def list_knowledge(
    topic: Optional[str] = Query(None, description="Filtre exact par topic"),
    is_active: Optional[bool] = Query(None, description="True/False ou omis"),
    search: Optional[str] = Query(None, description="Substring (slug/title/body)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ActorContext = Depends(_guard),
):
    """Liste paginée des fiches knowledge avec filtres."""
    items, total = product_repo.admin_list_knowledge(
        db,
        topic=topic,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    return KnowledgeListResponse(
        items=[KnowledgeRead.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@admin_router.get("/{slug}", response_model=KnowledgeRead)
def get_knowledge(
    slug: str,
    db: Session = Depends(get_db),
    _: ActorContext = Depends(_guard),
):
    """Détail d'une fiche par slug (inclut les inactives)."""
    item = product_repo.admin_get_knowledge(db, slug=slug)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return KnowledgeRead.model_validate(item)


@admin_router.post(
    "/",
    response_model=KnowledgeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge(
    payload: KnowledgeCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    """Crée une nouvelle fiche."""
    try:
        created = product_repo.create_knowledge(
            db,
            slug=payload.slug,
            topic=payload.topic,
            title=payload.title,
            body=payload.body,
            metadata=payload.metadata,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    db.commit()
    _safe_invalidate_catalog_cache(actor)
    _log_mutation("create", payload.slug, actor)
    return KnowledgeRead.model_validate(created)


@admin_router.put("/{slug}", response_model=KnowledgeRead)
def update_knowledge(
    slug: str,
    payload: KnowledgeUpdate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    """Met à jour une fiche (champs partiels)."""
    try:
        updated = product_repo.update_knowledge(
            db,
            slug=slug,
            topic=payload.topic,
            title=payload.title,
            body=payload.body,
            metadata=payload.metadata,
            is_active=payload.is_active,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not_found"
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    db.commit()
    _safe_invalidate_catalog_cache(actor)
    _log_mutation("update", slug, actor)
    return KnowledgeRead.model_validate(updated)


@admin_router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge(
    slug: str,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    """Supprime physiquement une fiche. Préférer ``is_active=false`` en général."""
    try:
        product_repo.delete_knowledge(db, slug=slug)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not_found"
        )

    db.commit()
    _safe_invalidate_catalog_cache(actor)
    _log_mutation("delete", slug, actor)
    return None
