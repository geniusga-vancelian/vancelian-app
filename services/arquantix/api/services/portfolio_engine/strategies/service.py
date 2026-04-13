"""Service layer for Strategies module (Portfolio Engine — strategy layer).

Covers both StrategyDefinition and StrategyInstance.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..portfolios.models import Portfolio
from ..sleeves.models import Sleeve
from .models import StrategyDefinition, StrategyInstance
from .repository import StrategyDefinitionRepository, StrategyInstanceRepository
from .schemas import DefinitionCreate, DefinitionUpdate, InstanceCreate, InstanceUpdate


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DefinitionNotFoundError(Exception):
    def __init__(self, definition_id: UUID):
        self.definition_id = definition_id
        super().__init__(f"StrategyDefinition {definition_id} not found")


class InstanceNotFoundError(Exception):
    def __init__(self, instance_id: UUID):
        self.instance_id = instance_id
        super().__init__(f"StrategyInstance {instance_id} not found")


class PortfolioReferenceError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class SleeveReferenceError(Exception):
    def __init__(self, sleeve_id: UUID):
        self.sleeve_id = sleeve_id
        super().__init__(f"Referenced sleeve {sleeve_id} does not exist")


class DefinitionReferenceError(Exception):
    def __init__(self, definition_id: UUID):
        self.definition_id = definition_id
        super().__init__(f"Referenced strategy definition {definition_id} does not exist")


class SleevePortfolioMismatchError(Exception):
    """Raised when sleeve_id does not belong to the specified portfolio_id."""

    def __init__(self, sleeve_id: UUID, portfolio_id: UUID):
        self.sleeve_id = sleeve_id
        self.portfolio_id = portfolio_id
        super().__init__(
            f"Sleeve {sleeve_id} does not belong to portfolio {portfolio_id}"
        )


# ---------------------------------------------------------------------------
# StrategyDefinitionService
# ---------------------------------------------------------------------------

class StrategyDefinitionService:

    def __init__(self) -> None:
        self._repo = StrategyDefinitionRepository()

    def create_definition(self, db: Session, payload: DefinitionCreate) -> StrategyDefinition:
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_definition(self, db: Session, definition_id: UUID) -> StrategyDefinition:
        definition = self._repo.get_by_id(db, definition_id)
        if definition is None:
            raise DefinitionNotFoundError(definition_id)
        return definition

    def list_definitions(
        self,
        db: Session,
        *,
        strategy_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[StrategyDefinition], int]:
        return self._repo.list(db, strategy_type=strategy_type, skip=skip, limit=limit)

    def update_definition(self, db: Session, definition_id: UUID, payload: DefinitionUpdate) -> StrategyDefinition:
        definition = self.get_definition(db, definition_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, definition, data=data)


# ---------------------------------------------------------------------------
# StrategyInstanceService
# ---------------------------------------------------------------------------

class StrategyInstanceService:

    def __init__(self) -> None:
        self._repo = StrategyInstanceRepository()

    @staticmethod
    def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
        if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first() is None:
            raise PortfolioReferenceError(portfolio_id)

    @staticmethod
    def _validate_definition_exists(db: Session, definition_id: UUID) -> None:
        if db.query(StrategyDefinition).filter(StrategyDefinition.id == definition_id).first() is None:
            raise DefinitionReferenceError(definition_id)

    @staticmethod
    def _validate_sleeve(db: Session, sleeve_id: UUID, portfolio_id: UUID) -> None:
        sleeve = db.query(Sleeve).filter(Sleeve.id == sleeve_id).first()
        if sleeve is None:
            raise SleeveReferenceError(sleeve_id)
        if sleeve.portfolio_id != portfolio_id:
            raise SleevePortfolioMismatchError(sleeve_id, portfolio_id)

    def create_instance(self, db: Session, payload: InstanceCreate) -> StrategyInstance:
        self._validate_portfolio_exists(db, payload.portfolio_id)
        self._validate_definition_exists(db, payload.strategy_definition_id)
        if payload.sleeve_id is not None:
            self._validate_sleeve(db, payload.sleeve_id, payload.portfolio_id)
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_instance(self, db: Session, instance_id: UUID) -> StrategyInstance:
        instance = self._repo.get_by_id(db, instance_id)
        if instance is None:
            raise InstanceNotFoundError(instance_id)
        return instance

    def list_instances_by_portfolio(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[StrategyInstance], int]:
        return self._repo.list_by_portfolio(db, portfolio_id, status=status, skip=skip, limit=limit)

    def update_instance(self, db: Session, instance_id: UUID, payload: InstanceUpdate) -> StrategyInstance:
        instance = self.get_instance(db, instance_id)
        data = payload.model_dump(exclude_unset=True)
        if "sleeve_id" in data and data["sleeve_id"] is not None:
            self._validate_sleeve(db, data["sleeve_id"], instance.portfolio_id)
        return self._repo.update(db, instance, data=data)
