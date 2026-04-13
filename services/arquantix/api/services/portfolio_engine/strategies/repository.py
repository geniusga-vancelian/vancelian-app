"""Repository layer for pe_strategy_definitions and pe_strategy_instances
(Portfolio Engine — strategy layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import StrategyDefinition, StrategyInstance


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DuplicateDefinitionCodeError(Exception):
    """Raised when a strategy definition with the same code already exists."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"StrategyDefinition with code '{code}' already exists")


# ---------------------------------------------------------------------------
# StrategyDefinitionRepository
# ---------------------------------------------------------------------------

class StrategyDefinitionRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> StrategyDefinition:
        definition = StrategyDefinition(**data)
        db.add(definition)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise DuplicateDefinitionCodeError(data.get("code", ""))
        return definition

    @staticmethod
    def get_by_id(db: Session, definition_id: UUID) -> Optional[StrategyDefinition]:
        return db.query(StrategyDefinition).filter(StrategyDefinition.id == definition_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        strategy_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[StrategyDefinition], int]:
        query = db.query(StrategyDefinition)
        if strategy_type:
            query = query.filter(StrategyDefinition.strategy_type == strategy_type)
        total = query.count()
        items = query.order_by(StrategyDefinition.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, definition: StrategyDefinition, *, data: dict) -> StrategyDefinition:
        for key, value in data.items():
            setattr(definition, key, value)
        db.flush()
        return definition


# ---------------------------------------------------------------------------
# StrategyInstanceRepository
# ---------------------------------------------------------------------------

class StrategyInstanceRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> StrategyInstance:
        instance = StrategyInstance(**data)
        db.add(instance)
        db.flush()
        return instance

    @staticmethod
    def get_by_id(db: Session, instance_id: UUID) -> Optional[StrategyInstance]:
        return db.query(StrategyInstance).filter(StrategyInstance.id == instance_id).first()

    @staticmethod
    def list_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[StrategyInstance], int]:
        query = db.query(StrategyInstance).filter(StrategyInstance.portfolio_id == portfolio_id)
        if status:
            query = query.filter(StrategyInstance.status == status)
        total = query.count()
        items = query.order_by(StrategyInstance.priority.asc(), StrategyInstance.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, instance: StrategyInstance, *, data: dict) -> StrategyInstance:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(instance, col_name, value)
        db.flush()
        return instance
