"""FastAPI router for TradingFeeConfig management."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from .schemas import (
    TradingFeeConfigCreate,
    TradingFeeConfigRead,
    TradingFeeConfigUpdate,
    TradingFeeConfigListResponse,
)
from .service import FeeConfigNotFoundError, TradingFeeConfigService

router = APIRouter()
_service = TradingFeeConfigService()


@router.get("", response_model=TradingFeeConfigListResponse)
def list_fee_configs(
    scope_type: Optional[str] = Query(None),
    scope_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    fee_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_configs(
        db, scope_type=scope_type, scope_id=scope_id,
        status=status, fee_type=fee_type, skip=skip, limit=limit,
    )
    return TradingFeeConfigListResponse(
        items=[TradingFeeConfigRead.model_validate(i) for i in items],
        total=total,
    )


@router.post("", response_model=TradingFeeConfigRead, status_code=201)
def create_fee_config(
    payload: TradingFeeConfigCreate,
    db: Session = Depends(get_db),
):
    config = _service.create_config(db, payload)
    db.commit()
    db.refresh(config)
    return TradingFeeConfigRead.model_validate(config)


@router.get("/{config_id}", response_model=TradingFeeConfigRead)
def get_fee_config(config_id: UUID, db: Session = Depends(get_db)):
    try:
        config = _service.get_config(db, config_id)
    except FeeConfigNotFoundError:
        raise HTTPException(status_code=404, detail="Fee config not found")
    return TradingFeeConfigRead.model_validate(config)


@router.patch("/{config_id}", response_model=TradingFeeConfigRead)
def update_fee_config(
    config_id: UUID,
    payload: TradingFeeConfigUpdate,
    db: Session = Depends(get_db),
):
    try:
        config = _service.update_config(db, config_id, payload)
    except FeeConfigNotFoundError:
        raise HTTPException(status_code=404, detail="Fee config not found")
    db.commit()
    db.refresh(config)
    return TradingFeeConfigRead.model_validate(config)
