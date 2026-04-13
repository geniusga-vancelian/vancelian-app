"""Service layer for Templates module (Portfolio Engine — catalog / template layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..instruments.models import Instrument
from ..products.models import ProductDefinition
from ..strategies.models import StrategyDefinition
from .models import PortfolioTemplate, TemplateAllocation
from .repository import PortfolioTemplateRepository, TemplateAllocationRepository
from .schemas import (
    TemplateAllocationCreate,
    TemplateAllocationUpdate,
    TemplateCreate,
    TemplateUpdate,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TemplateNotFoundError(Exception):
    def __init__(self, template_id: UUID):
        self.template_id = template_id
        super().__init__(f"PortfolioTemplate {template_id} not found")


class TemplateAllocationNotFoundError(Exception):
    def __init__(self, allocation_id: UUID):
        self.allocation_id = allocation_id
        super().__init__(f"TemplateAllocation {allocation_id} not found")


class ProductReferenceError(Exception):
    def __init__(self, product_id: UUID):
        self.product_id = product_id
        super().__init__(f"Referenced product {product_id} does not exist")


class InstrumentReferenceError(Exception):
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        super().__init__(f"Referenced instrument {instrument_id} does not exist")


class StrategyDefinitionReferenceError(Exception):
    def __init__(self, strategy_definition_id: UUID):
        self.strategy_definition_id = strategy_definition_id
        super().__init__(f"Referenced strategy definition {strategy_definition_id} does not exist")


# ---------------------------------------------------------------------------
# Validators (same pattern as TargetAllocationService)
# ---------------------------------------------------------------------------

def _validate_product_exists(db: Session, product_id: UUID) -> None:
    if db.query(ProductDefinition).filter(ProductDefinition.id == product_id).first() is None:
        raise ProductReferenceError(product_id)


def _validate_instrument_exists(db: Session, instrument_id: UUID) -> None:
    if db.query(Instrument).filter(Instrument.id == instrument_id).first() is None:
        raise InstrumentReferenceError(instrument_id)


def _validate_strategy_definition_exists(db: Session, strategy_definition_id: UUID) -> None:
    if db.query(StrategyDefinition).filter(StrategyDefinition.id == strategy_definition_id).first() is None:
        raise StrategyDefinitionReferenceError(strategy_definition_id)


# ---------------------------------------------------------------------------
# PortfolioTemplate service
# ---------------------------------------------------------------------------

class PortfolioTemplateService:

    def __init__(self) -> None:
        self._repo = PortfolioTemplateRepository()

    def create_template(self, db: Session, payload: TemplateCreate) -> PortfolioTemplate:
        _validate_product_exists(db, payload.product_id)
        if payload.strategy_definition_id is not None:
            _validate_strategy_definition_exists(db, payload.strategy_definition_id)
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_template(self, db: Session, template_id: UUID) -> PortfolioTemplate:
        template = self._repo.get_by_id(db, template_id)
        if template is None:
            raise TemplateNotFoundError(template_id)
        return template

    def list_templates(
        self,
        db: Session,
        *,
        product_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple:
        return self._repo.list(db, product_id=product_id, skip=skip, limit=limit)

    def update_template(self, db: Session, template_id: UUID, payload: TemplateUpdate) -> PortfolioTemplate:
        template = self.get_template(db, template_id)
        data = payload.model_dump(exclude_unset=True)
        if "strategy_definition_id" in data and data["strategy_definition_id"] is not None:
            _validate_strategy_definition_exists(db, data["strategy_definition_id"])
        return self._repo.update(db, template, data=data)


# ---------------------------------------------------------------------------
# TemplateAllocation service
# ---------------------------------------------------------------------------

class TemplateAllocationService:

    def __init__(self) -> None:
        self._template_repo = PortfolioTemplateRepository()
        self._repo = TemplateAllocationRepository()

    def _validate_template_exists(self, db: Session, template_id: UUID) -> None:
        if self._template_repo.get_by_id(db, template_id) is None:
            raise TemplateNotFoundError(template_id)

    def create_allocation(self, db: Session, payload: TemplateAllocationCreate) -> TemplateAllocation:
        self._validate_template_exists(db, payload.template_id)
        _validate_instrument_exists(db, payload.instrument_id)
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_allocation(self, db: Session, allocation_id: UUID) -> TemplateAllocation:
        allocation = self._repo.get_by_id(db, allocation_id)
        if allocation is None:
            raise TemplateAllocationNotFoundError(allocation_id)
        return allocation

    def list_allocations_by_template(
        self,
        db: Session,
        template_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TemplateAllocation], int]:
        return self._repo.list_by_template(db, template_id, skip=skip, limit=limit)

    def update_allocation(self, db: Session, allocation_id: UUID, payload: TemplateAllocationUpdate) -> TemplateAllocation:
        allocation = self.get_allocation(db, allocation_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, allocation, data=data)

    def delete_allocation(self, db: Session, allocation_id: UUID) -> None:
        allocation = self.get_allocation(db, allocation_id)
        self._repo.delete(db, allocation)
