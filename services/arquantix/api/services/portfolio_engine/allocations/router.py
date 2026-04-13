"""Target Allocations API endpoints (Portfolio Engine).

Standalone endpoints: POST, GET/{id}, PATCH/{id}, DELETE/{id}.
The list endpoint GET /portfolios/{id}/target-allocations is nested in the portfolios router.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import AllocationCreate, AllocationRead, AllocationUpdate
from .repository import DuplicateAllocationError
from .service import (
    AllocationNotFoundError,
    InstrumentReferenceError,
    PortfolioReferenceError,
    SleeveReferenceError,
    TargetAllocationService,
)

router = APIRouter()

_service = TargetAllocationService()


@router.post("", response_model=AllocationRead, status_code=status.HTTP_201_CREATED)
def create_allocation(
    payload: AllocationCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        allocation = _service.create_allocation(db, payload)
        db.commit()
        db.refresh(allocation)
        return AllocationRead.model_validate(allocation)
    except (PortfolioReferenceError, SleeveReferenceError, InstrumentReferenceError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DuplicateAllocationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{allocation_id}", response_model=AllocationRead)
def get_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        allocation = _service.get_allocation(db, allocation_id)
        return AllocationRead.model_validate(allocation)
    except AllocationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TargetAllocation not found")


@router.patch("/{allocation_id}", response_model=AllocationRead)
def update_allocation(
    allocation_id: UUID,
    payload: AllocationUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        allocation = _service.update_allocation(db, allocation_id, payload)
        db.commit()
        db.refresh(allocation)
        return AllocationRead.model_validate(allocation)
    except AllocationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TargetAllocation not found")


@router.delete("/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        _service.delete_allocation(db, allocation_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AllocationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TargetAllocation not found")
