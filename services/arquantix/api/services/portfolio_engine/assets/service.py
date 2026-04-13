"""Service layer for Assets module (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import Asset
from .repository import AssetRepository, DuplicateSymbolError
from .schemas import AssetCreate, AssetUpdate


class AssetNotFoundError(Exception):
    def __init__(self, asset_id: UUID):
        self.asset_id = asset_id
        super().__init__(f"Asset {asset_id} not found")


class AssetService:

    def __init__(self) -> None:
        self._repo = AssetRepository()

    def create_asset(self, db: Session, payload: AssetCreate) -> Asset:
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_asset(self, db: Session, asset_id: UUID) -> Asset:
        asset = self._repo.get_by_id(db, asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id)
        return asset

    def list_assets(
        self,
        db: Session,
        *,
        asset_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Asset], int]:
        return self._repo.list(db, asset_type=asset_type, skip=skip, limit=limit)

    def update_asset(self, db: Session, asset_id: UUID, payload: AssetUpdate) -> Asset:
        asset = self.get_asset(db, asset_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, asset, data=data)
