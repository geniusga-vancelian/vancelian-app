"""Risk Policies API endpoints (Portfolio Engine).

Standalone endpoints: POST, GET/{id}, PATCH/{id}.
The nested endpoint GET /portfolios/{id}/risk-policy is in the portfolios router.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from .repository import DuplicateRiskPolicyError
from .schemas import RiskPolicyCreate, RiskPolicyRead, RiskPolicyUpdate
from .service import (
    PortfolioReferenceError,
    RiskPolicyNotFoundError,
    RiskPolicyService,
    SleeveReferenceError,
)

router = APIRouter()

_service = RiskPolicyService()


@router.post("", response_model=RiskPolicyRead, status_code=status.HTTP_201_CREATED)
def create_risk_policy(
    payload: RiskPolicyCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        policy = _service.create_policy(db, payload)
        db.commit()
        db.refresh(policy)
        return RiskPolicyRead.model_validate(policy)
    except (PortfolioReferenceError, SleeveReferenceError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DuplicateRiskPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{policy_id}", response_model=RiskPolicyRead)
def get_risk_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        policy = _service.get_policy(db, policy_id)
        return RiskPolicyRead.model_validate(policy)
    except RiskPolicyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RiskPolicy not found")


@router.patch("/{policy_id}", response_model=RiskPolicyRead)
def update_risk_policy(
    policy_id: UUID,
    payload: RiskPolicyUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        policy = _service.update_policy(db, policy_id, payload)
        db.commit()
        db.refresh(policy)
        return RiskPolicyRead.model_validate(policy)
    except RiskPolicyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RiskPolicy not found")
