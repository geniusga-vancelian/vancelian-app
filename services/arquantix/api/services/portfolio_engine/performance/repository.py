"""Repository layer for pe_portfolio_return_series (Phase 9 — Performance Engine).

Append-only: no update, no delete.
"""
from uuid import UUID

from sqlalchemy.orm import Session

from .models import PortfolioReturnSeries


class PerformanceRepository:

    @staticmethod
    def create_series_point(db: Session, *, data: dict) -> PortfolioReturnSeries:
        row = PortfolioReturnSeries(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def create_series_batch(db: Session, *, rows: list[dict]) -> list[PortfolioReturnSeries]:
        objects = [PortfolioReturnSeries(**d) for d in rows]
        db.add_all(objects)
        db.flush()
        return objects

    @staticmethod
    def list_series_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 500,
    ) -> tuple[list[PortfolioReturnSeries], int]:
        query = db.query(PortfolioReturnSeries).filter(
            PortfolioReturnSeries.portfolio_id == portfolio_id
        )
        total = query.count()
        items = (
            query.order_by(PortfolioReturnSeries.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total
