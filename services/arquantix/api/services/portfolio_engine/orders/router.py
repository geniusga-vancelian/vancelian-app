"""Orders API endpoints (Portfolio Engine — transaction layer)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action
from .schemas import OrderCreate, OrderListResponse, OrderRead
from .service import (
    ClientReferenceError,
    InstrumentReferenceError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    OrderService,
    PortfolioReferenceError,
)
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops

router = APIRouter()

_service = OrderService()
_guard = require_admin_or_ops()


def _dev(request: Request) -> str:
    return (request.headers.get("x-device-id") or "")[:128]


class RejectPayload(BaseModel):
    reason: str


@router.get("", response_model=OrderListResponse)
def list_orders(
    client_id: Optional[UUID] = Query(None),
    portfolio_id: Optional[UUID] = Query(None),
    order_type: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _service.list_orders(
        db, client_id=client_id, portfolio_id=portfolio_id,
        order_type=order_type, status=order_status, skip=skip, limit=limit,
    )
    return OrderListResponse(
        items=[OrderRead.model_validate(o) for o in items],
        total=total,
    )


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    request: Request,
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        order = _service.create_order(db, payload)
        db.commit()
        db.refresh(order)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={"endpoint": "POST /api/portfolio-engine/orders", "order_id": str(order.id)},
        )
        db.commit()
        return OrderRead.model_validate(order)
    except ClientReferenceError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"client_reference:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except PortfolioReferenceError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"portfolio_reference:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
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


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        order = _service.get_order(db, order_id)
        return OrderRead.model_validate(order)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


@router.post("/{order_id}/accept", response_model=OrderRead)
def accept_order(
    request: Request,
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        order = _service.accept_order(db, order_id)
        db.commit()
        db.refresh(order)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={"endpoint": "POST /api/portfolio-engine/orders/{id}/accept", "order_id": str(order_id)},
        )
        db.commit()
        return OrderRead.model_validate(order)
    except OrderNotFoundError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="order_not_found",
            extra={"order_id": str(order_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    except InvalidStatusTransitionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_status:{exc}",
            extra={"order_id": str(order_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{order_id}/reject", response_model=OrderRead)
def reject_order(
    request: Request,
    order_id: UUID,
    payload: RejectPayload,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        order = _service.reject_order(db, order_id, payload.reason)
        db.commit()
        db.refresh(order)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={"endpoint": "POST /api/portfolio-engine/orders/{id}/reject", "order_id": str(order_id)},
        )
        db.commit()
        return OrderRead.model_validate(order)
    except OrderNotFoundError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="order_not_found",
            extra={"order_id": str(order_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    except InvalidStatusTransitionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_status:{exc}",
            extra={"order_id": str(order_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    request: Request,
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        order = _service.cancel_order(db, order_id)
        db.commit()
        db.refresh(order)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={"endpoint": "POST /api/portfolio-engine/orders/{id}/cancel", "order_id": str(order_id)},
        )
        db.commit()
        return OrderRead.model_validate(order)
    except OrderNotFoundError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="order_not_found",
            extra={"order_id": str(order_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    except InvalidStatusTransitionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_status:{exc}",
            extra={"order_id": str(order_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
