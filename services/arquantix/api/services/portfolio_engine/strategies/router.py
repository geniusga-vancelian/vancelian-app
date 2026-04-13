"""Strategies API endpoints (Portfolio Engine — strategy layer).

Exports two routers:
- definitions_router: GET/POST /strategy-definitions
- instances_router: POST /strategy-instances, PATCH /strategy-instances/{id}

The nested list GET /portfolios/{id}/strategies is in the portfolios router.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .repository import DuplicateDefinitionCodeError
from .schemas import (
    DefinitionCreate,
    DefinitionListResponse,
    DefinitionRead,
    DefinitionUpdate,
    InstanceCreate,
    InstanceRead,
    InstanceUpdate,
)
from .service import (
    DefinitionNotFoundError,
    DefinitionReferenceError,
    InstanceNotFoundError,
    PortfolioReferenceError,
    SleevePortfolioMismatchError,
    SleeveReferenceError,
    StrategyDefinitionService,
    StrategyInstanceService,
)

# ---------------------------------------------------------------------------
# Strategy Definitions router
# ---------------------------------------------------------------------------

definitions_router = APIRouter()

_def_service = StrategyDefinitionService()


@definitions_router.get("", response_model=DefinitionListResponse)
def list_definitions(
    strategy_type: Optional[str] = Query(None, description="Filter by strategy_type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _def_service.list_definitions(
        db, strategy_type=strategy_type, skip=skip, limit=limit,
    )
    return DefinitionListResponse(
        items=[DefinitionRead.model_validate(d) for d in items],
        total=total,
    )


@definitions_router.post("", response_model=DefinitionRead, status_code=status.HTTP_201_CREATED)
def create_definition(
    payload: DefinitionCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        definition = _def_service.create_definition(db, payload)
        db.commit()
        db.refresh(definition)
        return DefinitionRead.model_validate(definition)
    except DuplicateDefinitionCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@definitions_router.get("/{definition_id}", response_model=DefinitionRead)
def get_definition(
    definition_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        definition = _def_service.get_definition(db, definition_id)
        return DefinitionRead.model_validate(definition)
    except DefinitionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StrategyDefinition not found")


@definitions_router.patch("/{definition_id}", response_model=DefinitionRead)
def update_definition(
    definition_id: UUID,
    payload: DefinitionUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        definition = _def_service.update_definition(db, definition_id, payload)
        db.commit()
        db.refresh(definition)
        return DefinitionRead.model_validate(definition)
    except DefinitionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StrategyDefinition not found")


# ---------------------------------------------------------------------------
# Strategy Instances router
# ---------------------------------------------------------------------------

instances_router = APIRouter()

_inst_service = StrategyInstanceService()


@instances_router.post("", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
def create_instance(
    payload: InstanceCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        instance = _inst_service.create_instance(db, payload)
        db.commit()
        db.refresh(instance)
        return InstanceRead.model_validate(instance)
    except PortfolioReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DefinitionReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SleeveReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SleevePortfolioMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@instances_router.get("/{instance_id}", response_model=InstanceRead)
def get_instance(
    instance_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        instance = _inst_service.get_instance(db, instance_id)
        return InstanceRead.model_validate(instance)
    except InstanceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StrategyInstance not found")


@instances_router.patch("/{instance_id}", response_model=InstanceRead)
def update_instance(
    instance_id: UUID,
    payload: InstanceUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        instance = _inst_service.update_instance(db, instance_id, payload)
        db.commit()
        db.refresh(instance)
        return InstanceRead.model_validate(instance)
    except InstanceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StrategyInstance not found")
    except SleeveReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SleevePortfolioMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# Keep a combined router for backward-compatible import in portfolio_engine/router.py
router = APIRouter()
