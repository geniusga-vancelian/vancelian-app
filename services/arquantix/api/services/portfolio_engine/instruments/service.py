"""Service layer for Instruments module (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..assets.models import Asset
from .models import Instrument
from .repository import InstrumentRepository
from .schemas import InstrumentCreate, InstrumentUpdate


class InstrumentNotFoundError(Exception):
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        super().__init__(f"Instrument {instrument_id} not found")


class AssetReferenceError(Exception):
    """Raised when the referenced asset_id does not exist."""

    def __init__(self, asset_id: UUID):
        self.asset_id = asset_id
        super().__init__(f"Referenced asset {asset_id} does not exist")


class InstrumentService:

    def __init__(self) -> None:
        self._repo = InstrumentRepository()

    def _validate_asset_exists(self, db: Session, asset_id: UUID) -> None:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset is None:
            raise AssetReferenceError(asset_id)

    def create_instrument(self, db: Session, payload: InstrumentCreate) -> Instrument:
        self._validate_asset_exists(db, payload.asset_id)
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_instrument(self, db: Session, instrument_id: UUID) -> Instrument:
        instrument = self._repo.get_by_id(db, instrument_id)
        if instrument is None:
            raise InstrumentNotFoundError(instrument_id)
        return instrument

    def list_instruments(
        self,
        db: Session,
        *,
        instrument_type: Optional[str] = None,
        asset_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Instrument], int]:
        return self._repo.list(
            db, instrument_type=instrument_type, asset_id=asset_id, skip=skip, limit=limit,
        )

    def update_instrument(self, db: Session, instrument_id: UUID, payload: InstrumentUpdate) -> Instrument:
        instrument = self.get_instrument(db, instrument_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, instrument, data=data)
