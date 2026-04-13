"""Trades API endpoints (Portfolio Engine — transaction layer).

POST is available for recording trades (admin/internal).
No PATCH or DELETE — trades are immutable.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action
from .schemas import TradeCreate, TradeListResponse, TradeRead
from .service import (
    InstrumentReferenceError,
    OrderNotExecutableError,
    OrderReferenceError,
    TradeNotFoundError,
    TradeService,
)
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops

router = APIRouter()

_service = TradeService()
_guard = require_admin_or_ops()


def _dev(request: Request) -> str:
    return (request.headers.get("x-device-id") or "")[:128]


@router.get("", response_model=TradeListResponse)
def list_trades(
    order_id: Optional[UUID] = Query(None),
    instrument_id: Optional[UUID] = Query(None),
    side: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _service.list_trades(
        db, order_id=order_id, instrument_id=instrument_id,
        side=side, skip=skip, limit=limit,
    )
    return TradeListResponse(
        items=[TradeRead.model_validate(t) for t in items],
        total=total,
    )


@router.post("", response_model=TradeRead, status_code=status.HTTP_201_CREATED)
def record_trade(
    request: Request,
    payload: TradeCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        trade = _service.record_trade(db, payload)
        db.commit()
        db.refresh(trade)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/trades",
                "trade_id": str(trade.id),
                "order_id": str(payload.order_id),
            },
        )
        db.commit()
        return TradeRead.model_validate(trade)
    except OrderReferenceError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"order_reference:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except OrderNotExecutableError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"order_not_executable:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InstrumentReferenceError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"instrument_reference:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{trade_id}", response_model=TradeRead)
def get_trade(
    trade_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        trade = _service.get_trade(db, trade_id)
        return TradeRead.model_validate(trade)
    except TradeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
