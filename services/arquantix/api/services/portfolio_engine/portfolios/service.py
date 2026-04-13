"""Service layer for Portfolios module (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..products.models import ProductDefinition
from .models import Portfolio
from .repository import PortfolioRepository
from .schemas import PortfolioCreate, PortfolioUpdate


class PortfolioNotFoundError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class OriginProductReferenceError(Exception):
    def __init__(self, product_id: UUID):
        self.product_id = product_id
        super().__init__(f"Referenced origin product {product_id} does not exist")


class PortfolioService:

    def __init__(self) -> None:
        self._repo = PortfolioRepository()

    @staticmethod
    def _validate_origin_product_exists(db: Session, product_id: UUID) -> None:
        if db.query(ProductDefinition).filter(ProductDefinition.id == product_id).first() is None:
            raise OriginProductReferenceError(product_id)

    def create_portfolio(self, db: Session, payload: PortfolioCreate) -> Portfolio:
        # TODO: validate client_id exists when the clients module is implemented.
        if payload.origin_product_id is not None:
            self._validate_origin_product_exists(db, payload.origin_product_id)
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_portfolio(self, db: Session, portfolio_id: UUID) -> Portfolio:
        portfolio = self._repo.get_by_id(db, portfolio_id)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_id)
        return portfolio

    def list_portfolios(
        self,
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        client_ids: Optional[list[UUID]] = None,
        portfolio_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Portfolio], int]:
        return self._repo.list(
            db, client_id=client_id, client_ids=client_ids,
            portfolio_type=portfolio_type, status=status,
            skip=skip, limit=limit,
        )

    def update_portfolio(self, db: Session, portfolio_id: UUID, payload: PortfolioUpdate) -> Portfolio:
        portfolio = self.get_portfolio(db, portfolio_id)
        data = payload.model_dump(exclude_unset=True)
        if "origin_product_id" in data and data["origin_product_id"] is not None:
            self._validate_origin_product_exists(db, data["origin_product_id"])
        return self._repo.update(db, portfolio, data=data)
