"""Assets API endpoints (Portfolio Engine — registry layer)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .repository import DuplicateSymbolError
from .schemas import AssetCreate, AssetListResponse, AssetRead, AssetUpdate
from .service import AssetNotFoundError, AssetService

router = APIRouter()

_service = AssetService()


@router.get("", response_model=AssetListResponse)
def list_assets(
    asset_type: Optional[str] = Query(None, description="Filter by asset_type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_assets(db, asset_type=asset_type, skip=skip, limit=limit)
    return AssetListResponse(
        data=[AssetRead.model_validate(a) for a in items],
        total=total,
    )


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        asset = _service.create_asset(db, payload)
        db.commit()
        db.refresh(asset)
        return AssetRead.model_validate(asset)
    except DuplicateSymbolError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        asset = _service.get_asset(db, asset_id)
        return AssetRead.model_validate(asset)
    except AssetNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: UUID,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        asset = _service.update_asset(db, asset_id, payload)
        db.commit()
        db.refresh(asset)
        return AssetRead.model_validate(asset)
    except AssetNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
