"""Repository layer for pe_portfolios (Portfolio Engine — Portfolios module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import Portfolio


class PortfolioRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> Portfolio:
        portfolio = Portfolio(**data)
        db.add(portfolio)
        db.flush()
        return portfolio

    @staticmethod
    def get_by_id(db: Session, portfolio_id: UUID) -> Optional[Portfolio]:
        return db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        client_ids: Optional[list[UUID]] = None,
        portfolio_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Portfolio], int]:
        query = db.query(Portfolio)
        if client_id:
            query = query.filter(Portfolio.client_id == client_id)
        elif client_ids is not None:
            query = query.filter(Portfolio.client_id.in_(client_ids))
        if portfolio_type:
            query = query.filter(Portfolio.portfolio_type == portfolio_type)
        if status:
            query = query.filter(Portfolio.status == status)
        total = query.count()
        items = query.order_by(Portfolio.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, portfolio: Portfolio, *, data: dict) -> Portfolio:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(portfolio, col_name, value)
        db.flush()
        return portfolio
