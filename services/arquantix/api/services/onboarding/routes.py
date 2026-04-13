"""
FastAPI routes for onboarding step engine.

Même préfixe ``/api/persons/{person_id}/...`` que ``services.persons.routes`` mais
**pas** les endpoints legacy GET/POST personne brute : ce module est le flux
onboarding par étapes. Auth encore à câbler (TODO ci-dessous) — ne pas confondre
avec la dépréciation Phase 4C des routes ``/{id}`` et ``/{id}/fields``.
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from database import get_db
from services.onboarding_engine import get_next_step, submit_step
from schemas_jurisdiction import NextStepResponse, SubmitStepRequest, SubmitStepResponse

router = APIRouter(prefix="/api/persons", tags=["onboarding"])


@router.get("/{person_id}/onboarding/next-step", response_model=NextStepResponse)
def get_next_onboarding_step(
    person_id: uuid.UUID,
    jurisdiction: str = Query(...),
    purpose: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Get the next step for a person's onboarding.
    """
    try:
        result = get_next_step(db=db, person_id=person_id, jurisdiction=jurisdiction, purpose=purpose)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{person_id}/onboarding/submit-step", response_model=SubmitStepResponse)
def submit_onboarding_step(
    person_id: uuid.UUID,
    request: SubmitStepRequest,
    jurisdiction: str = Query(...),
    purpose: str = Query(...),
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user),  # TODO: wire auth
):
    """
    Submit step values and return next step.
    """
    try:
        # Stub actor from auth (TODO: wire real auth)
        actor_type = "user"  # TODO: derive from current_user
        actor_id = None  # TODO: derive from current_user.email or current_user.id
        
        result = submit_step(
            db=db,
            person_id=person_id,
            step_id=request.step_id,
            values=request.values,
            jurisdiction=jurisdiction,
            purpose=purpose,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=request.correlation_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
