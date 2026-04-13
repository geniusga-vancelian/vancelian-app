"""Service layer for Rebalance Policies module (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..portfolios.models import Portfolio
from ..sleeves.models import Sleeve
from .models import RebalancePolicy
from .repository import RebalancePolicyRepository
from .schemas import RebalancePolicyCreate, RebalancePolicyUpdate


class PolicyNotFoundError(Exception):
    def __init__(self, policy_id: UUID):
        self.policy_id = policy_id
        super().__init__(f"RebalancePolicy {policy_id} not found")


class PortfolioReferenceError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class SleeveReferenceError(Exception):
    def __init__(self, sleeve_id: UUID):
        self.sleeve_id = sleeve_id
        super().__init__(f"Referenced sleeve {sleeve_id} does not exist")


class RebalancePolicyService:

    def __init__(self) -> None:
        self._repo = RebalancePolicyRepository()

    @staticmethod
    def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
        if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first() is None:
            raise PortfolioReferenceError(portfolio_id)

    @staticmethod
    def _validate_sleeve_exists(db: Session, sleeve_id: UUID) -> None:
        if db.query(Sleeve).filter(Sleeve.id == sleeve_id).first() is None:
            raise SleeveReferenceError(sleeve_id)

    def create_policy(self, db: Session, payload: RebalancePolicyCreate) -> RebalancePolicy:
        if payload.portfolio_id is not None:
            self._validate_portfolio_exists(db, payload.portfolio_id)
        if payload.sleeve_id is not None:
            self._validate_sleeve_exists(db, payload.sleeve_id)
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_policy(self, db: Session, policy_id: UUID) -> RebalancePolicy:
        policy = self._repo.get_by_id(db, policy_id)
        if policy is None:
            raise PolicyNotFoundError(policy_id)
        return policy

    def get_policy_by_portfolio(self, db: Session, portfolio_id: UUID) -> Optional[RebalancePolicy]:
        return self._repo.get_by_portfolio(db, portfolio_id)

    def list_policies_by_portfolio(
        self,
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[RebalancePolicy], int]:
        return self._repo.list_by_portfolio(db, portfolio_id, skip=skip, limit=limit)

    def update_policy(self, db: Session, policy_id: UUID, payload: RebalancePolicyUpdate) -> RebalancePolicy:
        policy = self.get_policy(db, policy_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, policy, data=data)
