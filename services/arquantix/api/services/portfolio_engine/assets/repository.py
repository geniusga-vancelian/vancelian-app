"""Repository layer for pe_assets (Portfolio Engine — Assets module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Asset


class DuplicateSymbolError(Exception):
    """Raised when attempting to create an asset with a symbol that already exists."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Asset with symbol '{symbol}' already exists")


class AssetRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> Asset:
        asset = Asset(**data)
        db.add(asset)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise DuplicateSymbolError(data.get("symbol", ""))
        return asset

    @staticmethod
    def get_by_id(db: Session, asset_id: UUID) -> Optional[Asset]:
        return db.query(Asset).filter(Asset.id == asset_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        asset_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Asset], int]:
        query = db.query(Asset)
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        total = query.count()
        items = query.order_by(Asset.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, asset: Asset, *, data: dict) -> Asset:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(asset, col_name, value)
        db.flush()
        return asset
