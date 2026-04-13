"""Rebalance Policies API endpoints (Portfolio Engine).

Standalone endpoints: POST, GET/{id}, PATCH/{id}.
The nested endpoint GET /portfolios/{id}/rebalance-policy is in the portfolios router.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import RebalancePolicyCreate, RebalancePolicyRead, RebalancePolicyUpdate
from .repository import DuplicatePolicyError
from .service import (
    PolicyNotFoundError,
    PortfolioReferenceError,
    RebalancePolicyService,
    SleeveReferenceError,
)

router = APIRouter()

_service = RebalancePolicyService()


@router.post("", response_model=RebalancePolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: RebalancePolicyCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        policy = _service.create_policy(db, payload)
        db.commit()
        db.refresh(policy)
        return RebalancePolicyRead.model_validate(policy)
    except (PortfolioReferenceError, SleeveReferenceError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DuplicatePolicyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{policy_id}", response_model=RebalancePolicyRead)
def get_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        policy = _service.get_policy(db, policy_id)
        return RebalancePolicyRead.model_validate(policy)
    except PolicyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RebalancePolicy not found")


@router.patch("/{policy_id}", response_model=RebalancePolicyRead)
def update_policy(
    policy_id: UUID,
    payload: RebalancePolicyUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        policy = _service.update_policy(db, policy_id, payload)
        db.commit()
        db.refresh(policy)
        return RebalancePolicyRead.model_validate(policy)
    except PolicyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RebalancePolicy not found")
