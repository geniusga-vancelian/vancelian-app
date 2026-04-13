"""
FastAPI routes for AML risk scoring.

Préfixe ``/api/persons/{person_id}/risk/...`` — distinct des endpoints legacy
Phase 4C (GET personne, POST fields). Couverture auth à renforcer séparément.
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from database import get_db
from services.aml_risk_engine import compute_aml_risk, get_latest_risk
from schemas_aml_risk import ComputeRiskResponse, LatestRiskResponse

router = APIRouter(prefix="/api/persons", tags=["aml-risk"])


@router.post("/{person_id}/risk/compute", response_model=ComputeRiskResponse)
def compute_risk(
    person_id: uuid.UUID,
    jurisdiction: str = Query(...),
    correlation_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user),  # TODO: wire auth
):
    """
    Compute AML risk score for a person.
    """
    try:
        # Stub actor from auth (TODO: wire real auth)
        actor_type = "system"  # TODO: derive from current_user
        actor_id = None  # TODO: derive from current_user.email or current_user.id
        
        result = compute_aml_risk(
            db=db,
            person_id=person_id,
            jurisdiction=jurisdiction,
            correlation_id=correlation_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{person_id}/risk/latest", response_model=LatestRiskResponse)
def get_latest_risk_data(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Get latest risk data from derived fields and last audit event.
    """
    try:
        result = get_latest_risk(db=db, person_id=person_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
