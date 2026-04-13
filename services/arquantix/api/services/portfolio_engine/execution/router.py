"""Execution instructions API (Portfolio Engine — execution layer).

Provides admin / back-office / internal orchestration endpoints.
No delete endpoints. No arbitrary patch endpoints.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action
from .schemas import ExecutionCreate, ExecutionRead, ExecutionListResponse, FillReport
from .service import (
    ExecutionNotFoundError,
    ExecutionNotFillableError,
    ExecutionService,
    InstrumentReferenceError,
    InstrumentRequiredError,
    InvalidExecutionTransitionError,
    OrderReferenceError,
    ParentExecutionNotTerminalError,
    ParentExecutionReferenceError,
    PriceLimitRequiredError,
    QuantityOrAmountRequiredError,
    SideRequiredError,
)

router = APIRouter()
_service = ExecutionService()
_guard = require_admin_or_ops()


def _dev(request: Request) -> str:
    return (request.headers.get("x-device-id") or "")[:128]


def _map_error(e: Exception) -> HTTPException:
    if isinstance(e, ExecutionNotFoundError):
        return HTTPException(status_code=404, detail=str(e))
    if isinstance(e, InvalidExecutionTransitionError):
        return HTTPException(status_code=409, detail=str(e))
    if isinstance(e, ExecutionNotFillableError):
        return HTTPException(status_code=409, detail=str(e))
    if isinstance(e, (
        OrderReferenceError,
        InstrumentReferenceError,
        ParentExecutionReferenceError,
        ParentExecutionNotTerminalError,
        InstrumentRequiredError,
        SideRequiredError,
        QuantityOrAmountRequiredError,
        PriceLimitRequiredError,
    )):
        return HTTPException(status_code=422, detail=str(e))
    return HTTPException(status_code=500, detail=str(e))


class ReasonPayload(BaseModel):
    reason: str = Field(..., max_length=500)


class SendPayload(BaseModel):
    venue_order_id: Optional[str] = Field(None, max_length=255)


class AcknowledgePayload(BaseModel):
    venue_order_id: Optional[str] = Field(None, max_length=255)


@router.get("", response_model=ExecutionListResponse)
def list_executions(
    order_id: Optional[UUID] = None,
    venue: Optional[str] = None,
    execution_type: Optional[str] = None,
    status: Optional[str] = None,
    instrument_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_executions(
        db,
        order_id=order_id,
        venue=venue,
        execution_type=execution_type,
        status=status,
        instrument_id=instrument_id,
        skip=skip,
        limit=limit,
    )
    return ExecutionListResponse(
        items=[ExecutionRead.model_validate(i) for i in items],
        total=total,
    )


@router.post("", response_model=ExecutionRead, status_code=201)
def create_execution(
    request: Request,
    payload: ExecutionCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction = _service.create_execution(db, payload)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/executions",
                "execution_id": str(instruction.id),
            },
        )
        db.commit()
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)


@router.get("/{execution_id}", response_model=ExecutionRead)
def get_execution(execution_id: UUID, db: Session = Depends(get_db)):
    try:
        instruction = _service.get_execution(db, execution_id)
        return ExecutionRead.model_validate(instruction)
    except ExecutionNotFoundError as e:
        raise _map_error(e)


@router.post("/{execution_id}/send", response_model=ExecutionRead)
def send_execution(
    request: Request,
    execution_id: UUID,
    payload: SendPayload = SendPayload(),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction = _service.mark_sent(
            db, execution_id, venue_order_id=payload.venue_order_id
        )
        db.commit()
        db.refresh(instruction)
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)


@router.post("/{execution_id}/acknowledge", response_model=ExecutionRead)
def acknowledge_execution(
    request: Request,
    execution_id: UUID,
    payload: AcknowledgePayload = AcknowledgePayload(),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction = _service.mark_acknowledged(
            db, execution_id, venue_order_id=payload.venue_order_id
        )
        db.commit()
        db.refresh(instruction)
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)


@router.post("/{execution_id}/fill", response_model=ExecutionRead)
def fill_execution(
    request: Request,
    execution_id: UUID,
    payload: FillReport,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction, _trade = _service.process_fill(db, execution_id, payload)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/executions/{id}/fill",
                "execution_id": str(execution_id),
            },
        )
        db.commit()
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)


@router.post("/{execution_id}/reject", response_model=ExecutionRead)
def reject_execution(
    request: Request,
    execution_id: UUID,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction = _service.reject(db, execution_id, payload.reason)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/executions/{id}/reject",
                "execution_id": str(execution_id),
                "transition": "reject",
            },
        )
        db.commit()
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)


@router.post("/{execution_id}/expire", response_model=ExecutionRead)
def expire_execution(
    request: Request,
    execution_id: UUID,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction = _service.expire(db, execution_id)
        db.commit()
        db.refresh(instruction)
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)


@router.post("/{execution_id}/cancel", response_model=ExecutionRead)
def cancel_execution(
    request: Request,
    execution_id: UUID,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction = _service.cancel(db, execution_id)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/executions/{id}/cancel",
                "execution_id": str(execution_id),
                "transition": "cancel",
            },
        )
        db.commit()
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)


@router.post("/{execution_id}/fail", response_model=ExecutionRead)
def fail_execution(
    request: Request,
    execution_id: UUID,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    _ = actor
    try:
        instruction = _service.fail(db, execution_id, payload.reason)
        db.commit()
        db.refresh(instruction)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/executions/{id}/fail",
                "execution_id": str(execution_id),
                "transition": "fail",
            },
        )
        db.commit()
        return ExecutionRead.model_validate(instruction)
    except Exception as e:
        db.rollback()
        raise _map_error(e)
