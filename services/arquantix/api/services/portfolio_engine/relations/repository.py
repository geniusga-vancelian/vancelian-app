"""Repository layer for pe_position_relations (Portfolio Engine — relation layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import PositionRelation


class DuplicateRelationError(Exception):
    """Raised when the same (source, target, type) triple already exists."""

    def __init__(self, source_id: UUID, target_id: UUID, relation_type: str):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type
        super().__init__(
            f"Relation ({source_id} -> {target_id}, type={relation_type}) already exists"
        )


class PositionRelationRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> PositionRelation:
        relation = PositionRelation(**data)
        db.add(relation)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise DuplicateRelationError(
                data.get("source_position_id", ""),
                data.get("target_position_id", ""),
                data.get("relation_type", ""),
            )
        return relation

    @staticmethod
    def get_by_id(db: Session, relation_id: UUID) -> Optional[PositionRelation]:
        return db.query(PositionRelation).filter(PositionRelation.id == relation_id).first()

    @staticmethod
    def list_by_position(
        db: Session,
        position_id: UUID,
        *,
        relation_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PositionRelation], int]:
        """Return all relations where position_id is source OR target."""
        query = db.query(PositionRelation).filter(
            (PositionRelation.source_position_id == position_id)
            | (PositionRelation.target_position_id == position_id)
        )
        if relation_type:
            query = query.filter(PositionRelation.relation_type == relation_type)
        total = query.count()
        items = query.order_by(PositionRelation.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def delete(db: Session, relation: PositionRelation) -> None:
        db.delete(relation)
        db.flush()
