"""Repository layer for pe_risk_policies (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import RiskPolicy


class DuplicateRiskPolicyError(Exception):
    pass


class RiskPolicyRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> RiskPolicy:
        policy = RiskPolicy(**data)
        db.add(policy)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            if "uq_pe_risk_policies_" in str(exc.orig):
                raise DuplicateRiskPolicyError(
                    "A risk policy already exists for this context"
                ) from exc
            raise
        return policy

    @staticmethod
    def get_by_id(db: Session, policy_id: UUID) -> Optional[RiskPolicy]:
        return db.query(RiskPolicy).filter(RiskPolicy.id == policy_id).first()

    @staticmethod
    def get_by_portfolio(db: Session, portfolio_id: UUID) -> Optional[RiskPolicy]:
        return (
            db.query(RiskPolicy)
            .filter(RiskPolicy.portfolio_id == portfolio_id)
            .first()
        )

    @staticmethod
    def update(db: Session, policy: RiskPolicy, *, data: dict) -> RiskPolicy:
        for key, value in data.items():
            setattr(policy, key, value)
        db.flush()
        return policy
