"""Instruments API endpoints (Portfolio Engine — registry layer)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .repository import DuplicateCodeError
from .schemas import InstrumentCreate, InstrumentListResponse, InstrumentPriceRead, InstrumentRead, InstrumentUpdate
from .service import AssetReferenceError, InstrumentNotFoundError, InstrumentService
from .price_bridge import (
    get_instrument_price,
    InstrumentNotFoundError as PriceBridgeNotFoundError,
    MarketDataLinkMissingError,
    QuoteNotAvailableError,
)

router = APIRouter()

_service = InstrumentService()


@router.get("", response_model=InstrumentListResponse)
def list_instruments(
    instrument_type: Optional[str] = Query(None, description="Filter by instrument_type"),
    asset_id: Optional[UUID] = Query(None, description="Filter by asset_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_instruments(
        db, instrument_type=instrument_type, asset_id=asset_id, skip=skip, limit=limit,
    )
    return InstrumentListResponse(
        data=[InstrumentRead.model_validate(i) for i in items],
        total=total,
    )


@router.post("", response_model=InstrumentRead, status_code=status.HTTP_201_CREATED)
def create_instrument(
    payload: InstrumentCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        instrument = _service.create_instrument(db, payload)
        db.commit()
        db.refresh(instrument)
        return InstrumentRead.model_validate(instrument)
    except DuplicateCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except AssetReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{instrument_id}", response_model=InstrumentRead)
def get_instrument(
    instrument_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        instrument = _service.get_instrument(db, instrument_id)
        return InstrumentRead.model_validate(instrument)
    except InstrumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")


@router.get("/{instrument_id}/price", response_model=InstrumentPriceRead)
def get_instrument_current_price(
    instrument_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        result = get_instrument_price(db, instrument_id)
        return InstrumentPriceRead(**result)
    except PriceBridgeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not found",
        )
    except MarketDataLinkMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except QuoteNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch("/{instrument_id}", response_model=InstrumentRead)
def update_instrument(
    instrument_id: UUID,
    payload: InstrumentUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        instrument = _service.update_instrument(db, instrument_id, payload)
        db.commit()
        db.refresh(instrument)
        return InstrumentRead.model_validate(instrument)
    except InstrumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
