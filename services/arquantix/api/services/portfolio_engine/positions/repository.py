"""Repository layer for pe_position_atoms (Portfolio Engine — position layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .enums import ALLOWED_POSITION_TYPES
from .models import PositionAtom


class PositionAtomRepository:

    @staticmethod
    def _validate_position_type(position_type: str) -> None:
        if position_type not in ALLOWED_POSITION_TYPES:
            raise ValueError(
                f"position_type '{position_type}' is not allowed. "
                f"Allowed types: {sorted(t.value for t in ALLOWED_POSITION_TYPES)}"
            )

    @staticmethod
    def create(db: Session, *, data: dict) -> PositionAtom:
        PositionAtomRepository._validate_position_type(data.get("position_type", ""))
        position = PositionAtom(**data)
        db.add(position)
        db.flush()
        return position

    @staticmethod
    def get_by_id(db: Session, position_id: UUID) -> Optional[PositionAtom]:
        return db.query(PositionAtom).filter(PositionAtom.id == position_id).first()

    @staticmethod
    def find_open(
        db: Session,
        portfolio_id: UUID,
        instrument_id: UUID,
        *,
        for_update: bool = False,
    ) -> Optional[PositionAtom]:
        query = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.status == "open",
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    @staticmethod
    def list(
        db: Session,
        *,
        portfolio_id: Optional[UUID] = None,
        sleeve_id: Optional[UUID] = None,
        wallet_id: Optional[UUID] = None,
        instrument_id: Optional[UUID] = None,
        position_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PositionAtom], int]:
        query = db.query(PositionAtom)
        if portfolio_id:
            query = query.filter(PositionAtom.portfolio_id == portfolio_id)
        if sleeve_id:
            query = query.filter(PositionAtom.sleeve_id == sleeve_id)
        if wallet_id:
            query = query.filter(PositionAtom.wallet_id == wallet_id)
        if instrument_id:
            query = query.filter(PositionAtom.instrument_id == instrument_id)
        if position_type:
            query = query.filter(PositionAtom.position_type == position_type)
        if status:
            query = query.filter(PositionAtom.status == status)
        total = query.count()
        items = query.order_by(PositionAtom.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, position: PositionAtom, *, data: dict) -> PositionAtom:
        if "position_type" in data:
            PositionAtomRepository._validate_position_type(data["position_type"])
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(position, col_name, value)
        db.flush()
        return position
