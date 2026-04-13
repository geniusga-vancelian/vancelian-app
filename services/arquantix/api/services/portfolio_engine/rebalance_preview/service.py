"""Service layer for Rebalance Preview module (Portfolio Engine).

This service persists preview results only.
It does NOT compute drift, generate trades, or trigger execution.
TODO: The actual rebalance engine will call this service to persist its output.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..portfolios.models import Portfolio
from ..rebalancing.models import RebalancePolicy
from ..instruments.models import Instrument
from .models import RebalancePreview
from .repository import RebalancePreviewRepository
from .schemas import PreviewCreate


class PreviewNotFoundError(Exception):
    def __init__(self, preview_id: UUID):
        self.preview_id = preview_id
        super().__init__(f"RebalancePreview {preview_id} not found")


class PortfolioReferenceError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class PolicyReferenceError(Exception):
    def __init__(self, policy_id: UUID):
        self.policy_id = policy_id
        super().__init__(f"Referenced rebalance policy {policy_id} does not exist")


class InstrumentReferenceError(Exception):
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        super().__init__(f"Referenced instrument {instrument_id} does not exist")


class RebalancePreviewService:

    def __init__(self) -> None:
        self._repo = RebalancePreviewRepository()

    @staticmethod
    def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
        if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first() is None:
            raise PortfolioReferenceError(portfolio_id)

    @staticmethod
    def _validate_policy_exists(db: Session, policy_id: UUID) -> None:
        if db.query(RebalancePolicy).filter(RebalancePolicy.id == policy_id).first() is None:
            raise PolicyReferenceError(policy_id)

    @staticmethod
    def _validate_instrument_exists(db: Session, instrument_id: UUID) -> None:
        if db.query(Instrument).filter(Instrument.id == instrument_id).first() is None:
            raise InstrumentReferenceError(instrument_id)

    def create_preview(self, db: Session, payload: PreviewCreate) -> RebalancePreview:
        self._validate_portfolio_exists(db, payload.portfolio_id)
        if payload.rebalance_policy_id is not None:
            self._validate_policy_exists(db, payload.rebalance_policy_id)
        for item in payload.items:
            self._validate_instrument_exists(db, item.instrument_id)

        items_data = [it.model_dump() for it in payload.items]
        preview_data = payload.model_dump(exclude={"items"})
        return self._repo.create(db, data=preview_data, items_data=items_data)

    def get_preview(self, db: Session, preview_id: UUID) -> RebalancePreview:
        preview = self._repo.get_by_id(db, preview_id)
        if preview is None:
            raise PreviewNotFoundError(preview_id)
        return preview

    def get_latest_by_portfolio(self, db: Session, portfolio_id: UUID) -> Optional[RebalancePreview]:
        return self._repo.get_latest_by_portfolio(db, portfolio_id)

    def list_by_portfolio(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[RebalancePreview], int]:
        return self._repo.list_by_portfolio(db, portfolio_id, skip=skip, limit=limit)
