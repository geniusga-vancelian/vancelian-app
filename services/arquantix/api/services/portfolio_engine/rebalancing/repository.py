"""Repository layer for pe_rebalance_policies (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import RebalancePolicy


class DuplicatePolicyError(Exception):
    pass


class RebalancePolicyRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> RebalancePolicy:
        policy = RebalancePolicy(**data)
        db.add(policy)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            if "uq_pe_rebalance_policies_" in str(exc.orig):
                raise DuplicatePolicyError(
                    "A rebalance policy already exists for this context"
                ) from exc
            raise
        return policy

    @staticmethod
    def get_by_id(db: Session, policy_id: UUID) -> Optional[RebalancePolicy]:
        return db.query(RebalancePolicy).filter(RebalancePolicy.id == policy_id).first()

    @staticmethod
    def get_by_portfolio(db: Session, portfolio_id: UUID) -> Optional[RebalancePolicy]:
        return (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio_id)
            .first()
        )

    @staticmethod
    def list_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[RebalancePolicy], int]:
        query = db.query(RebalancePolicy).filter(RebalancePolicy.portfolio_id == portfolio_id)
        total = query.count()
        items = query.order_by(RebalancePolicy.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, policy: RebalancePolicy, *, data: dict) -> RebalancePolicy:
        for key, value in data.items():
            setattr(policy, key, value)
        db.flush()
        return policy
