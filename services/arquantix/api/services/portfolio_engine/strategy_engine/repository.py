"""Repository layer for pe_strategy_evaluations (Phase 7 — Strategy Engine).

Append-only: no update or delete operations.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import StrategyEvaluation


class StrategyEvaluationRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> StrategyEvaluation:
        evaluation = StrategyEvaluation(**data)
        db.add(evaluation)
        db.flush()
        return evaluation

    @staticmethod
    def list_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        signal_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[StrategyEvaluation], int]:
        query = db.query(StrategyEvaluation).filter(
            StrategyEvaluation.portfolio_id == portfolio_id
        )
        if signal_type:
            query = query.filter(StrategyEvaluation.signal_type == signal_type)
        total = query.count()
        items = (
            query.order_by(StrategyEvaluation.evaluation_timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def get_latest_by_instance(
        db: Session,
        strategy_instance_id: UUID,
        *,
        signal_type: Optional[str] = None,
    ) -> Optional[StrategyEvaluation]:
        query = db.query(StrategyEvaluation).filter(
            StrategyEvaluation.strategy_instance_id == strategy_instance_id
        )
        if signal_type:
            query = query.filter(StrategyEvaluation.signal_type == signal_type)
        return query.order_by(StrategyEvaluation.evaluation_timestamp.desc()).first()
