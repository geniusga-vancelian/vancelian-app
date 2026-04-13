"""Repository layer for pe_sleeves (Portfolio Engine — Sleeves module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import Sleeve


class SleeveRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> Sleeve:
        sleeve = Sleeve(**data)
        db.add(sleeve)
        db.flush()
        return sleeve

    @staticmethod
    def get_by_id(db: Session, sleeve_id: UUID) -> Optional[Sleeve]:
        return db.query(Sleeve).filter(Sleeve.id == sleeve_id).first()

    @staticmethod
    def list_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Sleeve], int]:
        query = db.query(Sleeve).filter(Sleeve.portfolio_id == portfolio_id)
        total = query.count()
        items = query.order_by(Sleeve.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, sleeve: Sleeve, *, data: dict) -> Sleeve:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(sleeve, col_name, value)
        db.flush()
        return sleeve
