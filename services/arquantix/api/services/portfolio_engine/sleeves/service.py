"""Service layer for Sleeves module (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..portfolios.models import Portfolio
from .models import Sleeve
from .repository import SleeveRepository
from .schemas import SleeveCreate, SleeveUpdate


class SleeveNotFoundError(Exception):
    def __init__(self, sleeve_id: UUID):
        self.sleeve_id = sleeve_id
        super().__init__(f"Sleeve {sleeve_id} not found")


class PortfolioReferenceError(Exception):
    """Raised when the referenced portfolio_id does not exist."""

    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class SleeveService:

    def __init__(self) -> None:
        self._repo = SleeveRepository()

    def _validate_portfolio_exists(self, db: Session, portfolio_id: UUID) -> None:
        pf = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if pf is None:
            raise PortfolioReferenceError(portfolio_id)

    def create_sleeve(self, db: Session, portfolio_id: UUID, payload: SleeveCreate) -> Sleeve:
        self._validate_portfolio_exists(db, portfolio_id)
        data = payload.model_dump()
        data["portfolio_id"] = portfolio_id
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_sleeve(self, db: Session, sleeve_id: UUID) -> Sleeve:
        sleeve = self._repo.get_by_id(db, sleeve_id)
        if sleeve is None:
            raise SleeveNotFoundError(sleeve_id)
        return sleeve

    def list_sleeves(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Sleeve], int]:
        return self._repo.list_by_portfolio(db, portfolio_id, skip=skip, limit=limit)

    def update_sleeve(self, db: Session, sleeve_id: UUID, payload: SleeveUpdate) -> Sleeve:
        sleeve = self.get_sleeve(db, sleeve_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, sleeve, data=data)
