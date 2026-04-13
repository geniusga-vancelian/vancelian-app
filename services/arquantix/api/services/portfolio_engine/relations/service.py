"""Service layer for Position Relations module (Portfolio Engine — relation layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..positions.models import PositionAtom
from .models import PositionRelation
from .repository import PositionRelationRepository
from .schemas import RelationCreate


class RelationNotFoundError(Exception):
    def __init__(self, relation_id: UUID):
        self.relation_id = relation_id
        super().__init__(f"PositionRelation {relation_id} not found")


class PositionReferenceError(Exception):
    """Raised when a referenced position does not exist."""

    def __init__(self, position_id: UUID, role: str = "position"):
        self.position_id = position_id
        super().__init__(f"Referenced {role} {position_id} does not exist")


class SelfRelationError(Exception):
    """Raised when source and target are the same position."""

    def __init__(self, position_id: UUID):
        self.position_id = position_id
        super().__init__(f"Cannot create a relation from position {position_id} to itself")


class PositionRelationService:

    def __init__(self) -> None:
        self._repo = PositionRelationRepository()

    @staticmethod
    def _validate_position_exists(db: Session, position_id: UUID, role: str = "position") -> None:
        if db.query(PositionAtom).filter(PositionAtom.id == position_id).first() is None:
            raise PositionReferenceError(position_id, role)

    def create_relation(self, db: Session, payload: RelationCreate) -> PositionRelation:
        if payload.source_position_id == payload.target_position_id:
            raise SelfRelationError(payload.source_position_id)
        self._validate_position_exists(db, payload.source_position_id, role="source position")
        self._validate_position_exists(db, payload.target_position_id, role="target position")
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_relation(self, db: Session, relation_id: UUID) -> PositionRelation:
        relation = self._repo.get_by_id(db, relation_id)
        if relation is None:
            raise RelationNotFoundError(relation_id)
        return relation

    def list_relations_for_position(
        self,
        db: Session,
        position_id: UUID,
        *,
        relation_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PositionRelation], int]:
        return self._repo.list_by_position(
            db, position_id, relation_type=relation_type, skip=skip, limit=limit,
        )

    def delete_relation(self, db: Session, relation_id: UUID) -> None:
        relation = self.get_relation(db, relation_id)
        self._repo.delete(db, relation)
