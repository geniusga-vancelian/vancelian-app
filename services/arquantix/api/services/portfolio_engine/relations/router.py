"""Position Relations API endpoints (Portfolio Engine — relation layer).

Standalone endpoints: POST, DELETE/{id}.
The list endpoint GET /positions/{id}/relations is nested in the positions router.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from .repository import DuplicateRelationError
from .schemas import RelationCreate, RelationRead
from .service import (
    PositionReferenceError,
    PositionRelationService,
    RelationNotFoundError,
    SelfRelationError,
)

router = APIRouter()

_service = PositionRelationService()


@router.post("", response_model=RelationRead, status_code=status.HTTP_201_CREATED)
def create_relation(
    payload: RelationCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        relation = _service.create_relation(db, payload)
        db.commit()
        db.refresh(relation)
        return RelationRead.model_validate(relation)
    except SelfRelationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except PositionReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DuplicateRelationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.delete("/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relation(
    relation_id: UUID,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        _service.delete_relation(db, relation_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except RelationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PositionRelation not found")
