"""Admin endpoints for advisor-client assignments (Authorization Scoping)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from ..security.context import ActorContext
from ..security.dependencies import require_admin_or_ops
from ..audit_service import AuditService
from .repository import AdvisorClientAssignmentRepository
from .schemas import (
    AdvisorClientAssignmentCreate,
    AdvisorClientAssignmentListResponse,
    AdvisorClientAssignmentRead,
    AdvisorClientAssignmentUpdate,
)

router = APIRouter()
_repo = AdvisorClientAssignmentRepository()
_audit = AuditService()
_guard = require_admin_or_ops()


@router.get("/advisor-assignments", response_model=AdvisorClientAssignmentListResponse)
def list_assignments(
    advisor_actor_id: Optional[str] = Query(None),
    client_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _repo.list_assignments(
        db,
        advisor_actor_id=advisor_actor_id,
        client_id=client_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return AdvisorClientAssignmentListResponse(
        items=[AdvisorClientAssignmentRead.model_validate(a) for a in items],
        total=total,
    )


@router.post(
    "/advisor-assignments",
    response_model=AdvisorClientAssignmentRead,
    status_code=201,
)
def create_assignment(
    body: AdvisorClientAssignmentCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    assignment = _repo.create(db, data={
        "advisor_actor_id": body.advisor_actor_id,
        "client_id": body.client_id,
        "status": body.status,
        "metadata_": body.metadata,
    })
    _audit.log_success(
        db,
        entity_type="advisor_assignment",
        entity_id=str(assignment.id),
        action="advisor_assignment_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        metadata={
            "advisor_actor_id": body.advisor_actor_id,
            "client_id": str(body.client_id),
        },
    )
    db.commit()
    db.refresh(assignment)
    return AdvisorClientAssignmentRead.model_validate(assignment)


@router.patch(
    "/advisor-assignments/{assignment_id}",
    response_model=AdvisorClientAssignmentRead,
)
def update_assignment(
    assignment_id: UUID,
    body: AdvisorClientAssignmentUpdate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    assignment = _repo.get_by_id(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")

    updates = {}
    if body.status is not None:
        updates["status"] = body.status
    if body.metadata is not None:
        updates["metadata_"] = body.metadata

    if updates:
        assignment = _repo.update(db, assignment, **updates)
        _audit.log_success(
            db,
            entity_type="advisor_assignment",
            entity_id=str(assignment.id),
            action="advisor_assignment_updated",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={"updated_fields": list(updates.keys())},
        )

    db.commit()
    db.refresh(assignment)
    return AdvisorClientAssignmentRead.model_validate(assignment)
