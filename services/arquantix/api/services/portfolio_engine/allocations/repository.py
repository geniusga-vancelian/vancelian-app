"""Repository layer for pe_target_allocations (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import TargetAllocation


class DuplicateAllocationError(Exception):
    pass


class TargetAllocationRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> TargetAllocation:
        allocation = TargetAllocation(**data)
        db.add(allocation)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            if "uq_pe_target_allocations_" in str(exc.orig):
                raise DuplicateAllocationError(
                    "An allocation for this instrument already exists in the target context"
                ) from exc
            raise
        return allocation

    @staticmethod
    def get_by_id(db: Session, allocation_id: UUID) -> Optional[TargetAllocation]:
        return db.query(TargetAllocation).filter(TargetAllocation.id == allocation_id).first()

    @staticmethod
    def list_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TargetAllocation], int]:
        query = db.query(TargetAllocation).filter(TargetAllocation.portfolio_id == portfolio_id)
        total = query.count()
        items = query.order_by(TargetAllocation.rebalance_priority.asc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def list_by_sleeve(
        db: Session,
        sleeve_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TargetAllocation], int]:
        query = db.query(TargetAllocation).filter(TargetAllocation.sleeve_id == sleeve_id)
        total = query.count()
        items = query.order_by(TargetAllocation.rebalance_priority.asc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, allocation: TargetAllocation, *, data: dict) -> TargetAllocation:
        for key, value in data.items():
            setattr(allocation, key, value)
        db.flush()
        return allocation

    @staticmethod
    def delete(db: Session, allocation: TargetAllocation) -> None:
        db.delete(allocation)
        db.flush()
