"""Templates API endpoints (Portfolio Engine — catalog / template layer).

templates_router  — CRUD for PortfolioTemplate  (/portfolio-templates)
allocations_router — CUD for TemplateAllocation  (/template-allocations)

The list endpoint for allocations is nested:
  GET /portfolio-templates/{id}/allocations
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database import get_db
from .repository import DuplicateTemplateAllocationError, DuplicateTemplateCodeError
from .schemas import (
    TemplateAllocationCreate,
    TemplateAllocationListResponse,
    TemplateAllocationRead,
    TemplateAllocationUpdate,
    TemplateCreate,
    TemplateListResponse,
    TemplateRead,
    TemplateUpdate,
)
from .service import (
    InstrumentReferenceError,
    PortfolioTemplateService,
    ProductReferenceError,
    StrategyDefinitionReferenceError,
    TemplateAllocationNotFoundError,
    TemplateAllocationService,
    TemplateNotFoundError,
)


# ---------------------------------------------------------------------------
# PortfolioTemplate router
# ---------------------------------------------------------------------------

templates_router = APIRouter()

_template_svc = PortfolioTemplateService()
_alloc_svc = TemplateAllocationService()


@templates_router.get("", response_model=TemplateListResponse)
def list_templates(
    product_id: Optional[UUID] = Query(None, description="Filter by product_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _template_svc.list_templates(db, product_id=product_id, skip=skip, limit=limit)
    return TemplateListResponse(
        items=[TemplateRead.model_validate(t) for t in items],
        total=total,
    )


@templates_router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
):
    try:
        template = _template_svc.create_template(db, payload)
        db.commit()
        db.refresh(template)
        return TemplateRead.model_validate(template)
    except (ProductReferenceError, StrategyDefinitionReferenceError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DuplicateTemplateCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@templates_router.get("/{template_id}", response_model=TemplateRead)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        template = _template_svc.get_template(db, template_id)
        return TemplateRead.model_validate(template)
    except TemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PortfolioTemplate not found")


@templates_router.patch("/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
):
    try:
        template = _template_svc.update_template(db, template_id, payload)
        db.commit()
        db.refresh(template)
        return TemplateRead.model_validate(template)
    except TemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PortfolioTemplate not found")
    except StrategyDefinitionReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@templates_router.get("/{template_id}/allocations", response_model=TemplateAllocationListResponse)
def list_template_allocations(
    template_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _alloc_svc.list_allocations_by_template(db, template_id, skip=skip, limit=limit)
    return TemplateAllocationListResponse(
        items=[TemplateAllocationRead.model_validate(a) for a in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# TemplateAllocation router (standalone CRUD minus list)
# ---------------------------------------------------------------------------

allocations_router = APIRouter()


@allocations_router.post("", response_model=TemplateAllocationRead, status_code=status.HTTP_201_CREATED)
def create_template_allocation(
    payload: TemplateAllocationCreate,
    db: Session = Depends(get_db),
):
    try:
        allocation = _alloc_svc.create_allocation(db, payload)
        db.commit()
        db.refresh(allocation)
        return TemplateAllocationRead.model_validate(allocation)
    except (TemplateNotFoundError, InstrumentReferenceError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DuplicateTemplateAllocationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@allocations_router.patch("/{allocation_id}", response_model=TemplateAllocationRead)
def update_template_allocation(
    allocation_id: UUID,
    payload: TemplateAllocationUpdate,
    db: Session = Depends(get_db),
):
    try:
        allocation = _alloc_svc.update_allocation(db, allocation_id, payload)
        db.commit()
        db.refresh(allocation)
        return TemplateAllocationRead.model_validate(allocation)
    except TemplateAllocationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TemplateAllocation not found")


@allocations_router.delete("/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        _alloc_svc.delete_allocation(db, allocation_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except TemplateAllocationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TemplateAllocation not found")
