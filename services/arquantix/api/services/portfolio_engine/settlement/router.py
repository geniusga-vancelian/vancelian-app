"""Settlement API endpoints (Portfolio Engine — settlement layer).

Admin/back-office endpoints for managing settlement instructions.
No DELETE or arbitrary PATCH — status transitions through dedicated action endpoints.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops
from .schemas import SettlementCreate, SettlementListResponse, SettlementRead
from .service import (
    AssetReferenceError,
    FromAccountReferenceError,
    InvalidSettlementTransitionError,
    OrderReferenceError,
    SameAccountError,
    SettlementNotFoundError,
    SettlementService,
    ToAccountReferenceError,
    TradeReferenceError,
)

router = APIRouter()

_service = SettlementService()
_guard = require_admin_or_ops()


def _dev(request: Request) -> str:
    return (request.headers.get("x-device-id") or "")[:128]


class ScheduleRequest(BaseModel):
    scheduled_at: datetime


class FailRequest(BaseModel):
    reason: str = Field(..., max_length=500)


class SettleRequest(BaseModel):
    external_reference: Optional[str] = Field(None, max_length=255)


@router.get("", response_model=SettlementListResponse)
def list_settlements(
    order_id: Optional[UUID] = Query(None),
    trade_id: Optional[UUID] = Query(None),
    settlement_group_id: Optional[UUID] = Query(None),
    settlement_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    from_account_id: Optional[UUID] = Query(None),
    to_account_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _service.list_settlements(
        db,
        order_id=order_id,
        trade_id=trade_id,
        settlement_group_id=settlement_group_id,
        settlement_type=settlement_type,
        status=status_filter,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        skip=skip,
        limit=limit,
    )
    return SettlementListResponse(
        items=[SettlementRead.model_validate(s) for s in items],
        total=total,
    )


@router.post("", response_model=SettlementRead, status_code=status.HTTP_201_CREATED)
def create_settlement(
    request: Request,
    payload: SettlementCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        instruction = _service.create_settlement(db, payload)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/settlements",
                "settlement_id": str(instruction.id),
            },
        )
        db.commit()
        return SettlementRead.model_validate(instruction)
    except SameAccountError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"same_account:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except (FromAccountReferenceError, ToAccountReferenceError) as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"account_reference:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except AssetReferenceError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"asset_reference:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
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
    except TradeReferenceError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"trade_reference:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{settlement_id}", response_model=SettlementRead)
def get_settlement(
    settlement_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        instruction = _service.get_settlement(db, settlement_id)
        return SettlementRead.model_validate(instruction)
    except SettlementNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SettlementInstruction not found")


@router.post("/{settlement_id}/schedule", response_model=SettlementRead)
def schedule_settlement(
    request: Request,
    settlement_id: UUID,
    payload: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        instruction = _service.mark_scheduled(db, settlement_id, payload.scheduled_at)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/settlements/{id}/schedule",
                "settlement_id": str(settlement_id),
            },
        )
        db.commit()
        return SettlementRead.model_validate(instruction)
    except SettlementNotFoundError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="settlement_not_found",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SettlementInstruction not found")
    except InvalidSettlementTransitionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_transition:{exc}",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{settlement_id}/start", response_model=SettlementRead)
def start_settlement(
    request: Request,
    settlement_id: UUID,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        instruction = _service.mark_in_progress(db, settlement_id)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/settlements/{id}/start",
                "settlement_id": str(settlement_id),
            },
        )
        db.commit()
        return SettlementRead.model_validate(instruction)
    except SettlementNotFoundError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="settlement_not_found",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SettlementInstruction not found")
    except InvalidSettlementTransitionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_transition:{exc}",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{settlement_id}/settle", response_model=SettlementRead)
def settle_settlement(
    request: Request,
    settlement_id: UUID,
    payload: SettleRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        instruction = _service.settle(
            db, settlement_id, external_reference=payload.external_reference
        )
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/settlements/{id}/settle",
                "settlement_id": str(settlement_id),
            },
        )
        db.commit()
        return SettlementRead.model_validate(instruction)
    except SettlementNotFoundError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="settlement_not_found",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SettlementInstruction not found")
    except InvalidSettlementTransitionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_transition:{exc}",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{settlement_id}/fail", response_model=SettlementRead)
def fail_settlement(
    request: Request,
    settlement_id: UUID,
    payload: FailRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        instruction = _service.fail(db, settlement_id, payload.reason)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/settlements/{id}/fail",
                "settlement_id": str(settlement_id),
            },
        )
        db.commit()
        return SettlementRead.model_validate(instruction)
    except SettlementNotFoundError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="settlement_not_found",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SettlementInstruction not found")
    except InvalidSettlementTransitionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_transition:{exc}",
            extra={"settlement_id": str(settlement_id)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
