"""Service layer for Target Allocations module (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..instruments.models import Instrument
from ..portfolios.models import Portfolio
from ..sleeves.models import Sleeve
from .models import TargetAllocation
from .repository import TargetAllocationRepository
from .schemas import AllocationCreate, AllocationUpdate


class AllocationNotFoundError(Exception):
    def __init__(self, allocation_id: UUID):
        self.allocation_id = allocation_id
        super().__init__(f"TargetAllocation {allocation_id} not found")


class PortfolioReferenceError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class SleeveReferenceError(Exception):
    def __init__(self, sleeve_id: UUID):
        self.sleeve_id = sleeve_id
        super().__init__(f"Referenced sleeve {sleeve_id} does not exist")


class InstrumentReferenceError(Exception):
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        super().__init__(f"Referenced instrument {instrument_id} does not exist")


class TargetAllocationService:

    def __init__(self) -> None:
        self._repo = TargetAllocationRepository()

    @staticmethod
    def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
        if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first() is None:
            raise PortfolioReferenceError(portfolio_id)

    @staticmethod
    def _validate_sleeve_exists(db: Session, sleeve_id: UUID) -> None:
        if db.query(Sleeve).filter(Sleeve.id == sleeve_id).first() is None:
            raise SleeveReferenceError(sleeve_id)

    @staticmethod
    def _validate_instrument_exists(db: Session, instrument_id: UUID) -> None:
        if db.query(Instrument).filter(Instrument.id == instrument_id).first() is None:
            raise InstrumentReferenceError(instrument_id)

    def create_allocation(self, db: Session, payload: AllocationCreate) -> TargetAllocation:
        if payload.portfolio_id is not None:
            self._validate_portfolio_exists(db, payload.portfolio_id)
        if payload.sleeve_id is not None:
            self._validate_sleeve_exists(db, payload.sleeve_id)
        self._validate_instrument_exists(db, payload.instrument_id)
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_allocation(self, db: Session, allocation_id: UUID) -> TargetAllocation:
        allocation = self._repo.get_by_id(db, allocation_id)
        if allocation is None:
            raise AllocationNotFoundError(allocation_id)
        return allocation

    def list_allocations_by_portfolio(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TargetAllocation], int]:
        return self._repo.list_by_portfolio(db, portfolio_id, skip=skip, limit=limit)

    def update_allocation(self, db: Session, allocation_id: UUID, payload: AllocationUpdate) -> TargetAllocation:
        allocation = self.get_allocation(db, allocation_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, allocation, data=data)

    def delete_allocation(self, db: Session, allocation_id: UUID) -> None:
        allocation = self.get_allocation(db, allocation_id)
        self._repo.delete(db, allocation)
