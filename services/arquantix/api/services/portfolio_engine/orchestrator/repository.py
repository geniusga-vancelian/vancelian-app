"""Repository layer for pe_orchestration_runs (Phase 8 — Rebalance Orchestrator)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import OrchestrationRun


class OrchestrationRunRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> OrchestrationRun:
        run = OrchestrationRun(**data)
        db.add(run)
        db.flush()
        return run

    @staticmethod
    def update(db: Session, run: OrchestrationRun, *, data: dict) -> OrchestrationRun:
        for key, value in data.items():
            setattr(run, key, value)
        db.flush()
        return run

    @staticmethod
    def get_by_id(db: Session, run_id: UUID) -> Optional[OrchestrationRun]:
        return db.query(OrchestrationRun).filter(OrchestrationRun.id == run_id).first()

    @staticmethod
    def list_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[OrchestrationRun], int]:
        query = db.query(OrchestrationRun).filter(
            OrchestrationRun.portfolio_id == portfolio_id
        )
        total = query.count()
        items = (
            query.order_by(OrchestrationRun.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total
