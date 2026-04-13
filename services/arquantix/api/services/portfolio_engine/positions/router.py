"""Position Atoms API endpoints (Portfolio Engine — position layer).

Standalone endpoints: POST, GET/{id}, PATCH/{id}.
The list endpoint GET /portfolios/{id}/positions is nested in the portfolios router.
Includes nested endpoint: GET /positions/{id}/relations.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import PositionCreate, PositionRead, PositionUpdate
from .service import (
    InstrumentReferenceError,
    ParentPositionReferenceError,
    PortfolioReferenceError,
    PositionAtomService,
    PositionNotFoundError,
    SleevePortfolioMismatchError,
    SleeveReferenceError,
    WalletReferenceError,
)
from ..relations.schemas import RelationListResponse, RelationRead
from ..relations.service import PositionRelationService

router = APIRouter()

_service = PositionAtomService()
_relation_service = PositionRelationService()


@router.post("", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
def create_position(
    payload: PositionCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        position = _service.create_position(db, payload)
        db.commit()
        db.refresh(position)
        return PositionRead.model_validate(position)
    except PortfolioReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except InstrumentReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except (SleeveReferenceError, WalletReferenceError, ParentPositionReferenceError, SleevePortfolioMismatchError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{position_id}", response_model=PositionRead)
def get_position(
    position_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        position = _service.get_position(db, position_id)
        return PositionRead.model_validate(position)
    except PositionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PositionAtom not found")


@router.patch("/{position_id}", response_model=PositionRead)
def update_position(
    position_id: UUID,
    payload: PositionUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        position = _service.update_position(db, position_id, payload)
        db.commit()
        db.refresh(position)
        return PositionRead.model_validate(position)
    except PositionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PositionAtom not found")
    except (SleeveReferenceError, WalletReferenceError, ParentPositionReferenceError, SleevePortfolioMismatchError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ── Nested relation endpoints ────────────────────────────────

@router.get("/{position_id}/relations", response_model=RelationListResponse)
def list_position_relations(
    position_id: UUID,
    relation_type: Optional[str] = Query(None, description="Filter by relation_type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        _service.get_position(db, position_id)
    except PositionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PositionAtom not found")

    items, total = _relation_service.list_relations_for_position(
        db, position_id, relation_type=relation_type, skip=skip, limit=limit,
    )
    return RelationListResponse(
        items=[RelationRead.model_validate(r) for r in items],
        total=total,
    )
