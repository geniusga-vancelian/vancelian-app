"""Repository layer for valuation snapshot persistence (Phase 5).

Append-only: no update, no delete.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import PortfolioValuation, PositionValuation


class ValuationRepository:

    @staticmethod
    def create_position_valuation(db: Session, *, data: dict) -> PositionValuation:
        row = PositionValuation(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def create_portfolio_valuation(db: Session, *, data: dict) -> PortfolioValuation:
        row = PortfolioValuation(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def list_portfolio_snapshots(
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PortfolioValuation], int]:
        query = db.query(PortfolioValuation).filter(
            PortfolioValuation.portfolio_id == portfolio_id
        )
        total = query.count()
        items = (
            query
            .order_by(PortfolioValuation.valuation_timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def list_position_snapshots(
        db: Session,
        portfolio_id: UUID,
        valuation_timestamp,
    ) -> list[PositionValuation]:
        return (
            db.query(PositionValuation)
            .filter(
                PositionValuation.portfolio_id == portfolio_id,
                PositionValuation.valuation_timestamp == valuation_timestamp,
            )
            .order_by(PositionValuation.created_at)
            .all()
        )
