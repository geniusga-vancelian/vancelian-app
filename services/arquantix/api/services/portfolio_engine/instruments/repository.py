"""Repository layer for pe_instruments (Portfolio Engine — Instruments module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Instrument


class DuplicateCodeError(Exception):
    """Raised when attempting to create an instrument with a code that already exists."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Instrument with code '{code}' already exists")


class InstrumentRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> Instrument:
        instrument = Instrument(**data)
        db.add(instrument)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise DuplicateCodeError(data.get("code", ""))
        return instrument

    @staticmethod
    def get_by_id(db: Session, instrument_id: UUID) -> Optional[Instrument]:
        return db.query(Instrument).filter(Instrument.id == instrument_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        instrument_type: Optional[str] = None,
        asset_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Instrument], int]:
        query = db.query(Instrument)
        if instrument_type:
            query = query.filter(Instrument.instrument_type == instrument_type)
        if asset_id:
            query = query.filter(Instrument.asset_id == asset_id)
        total = query.count()
        items = query.order_by(Instrument.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, instrument: Instrument, *, data: dict) -> Instrument:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(instrument, col_name, value)
        db.flush()
        return instrument
