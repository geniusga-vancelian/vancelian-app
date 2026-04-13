"""Repository for pe_advisor_client_assignments."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import AdvisorClientAssignment


class AdvisorClientAssignmentRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> AdvisorClientAssignment:
        row = AdvisorClientAssignment(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def get_by_id(db: Session, assignment_id: UUID) -> Optional[AdvisorClientAssignment]:
        return (
            db.query(AdvisorClientAssignment)
            .filter(AdvisorClientAssignment.id == assignment_id)
            .first()
        )

    @staticmethod
    def get_active_client_ids(db: Session, advisor_actor_id: str) -> list[UUID]:
        rows = (
            db.query(AdvisorClientAssignment.client_id)
            .filter(
                AdvisorClientAssignment.advisor_actor_id == advisor_actor_id,
                AdvisorClientAssignment.status == "active",
            )
            .all()
        )
        return [r[0] for r in rows]

    @staticmethod
    def list_assignments(
        db: Session,
        *,
        advisor_actor_id: Optional[str] = None,
        client_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AdvisorClientAssignment], int]:
        query = db.query(AdvisorClientAssignment)
        if advisor_actor_id:
            query = query.filter(AdvisorClientAssignment.advisor_actor_id == advisor_actor_id)
        if client_id:
            query = query.filter(AdvisorClientAssignment.client_id == client_id)
        if status:
            query = query.filter(AdvisorClientAssignment.status == status)
        total = query.count()
        items = query.order_by(AdvisorClientAssignment.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, assignment: AdvisorClientAssignment, **kwargs) -> AdvisorClientAssignment:
        for k, v in kwargs.items():
            setattr(assignment, k, v)
        db.flush()
        return assignment
