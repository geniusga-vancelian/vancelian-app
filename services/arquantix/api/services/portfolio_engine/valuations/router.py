"""FastAPI router for Valuation & Performance Engine (Phase 5).

Endpoints are resource-nested under /portfolios/ and /positions/,
mounted without prefix in the main router (like the summary module).
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from .schemas import (
    PortfolioValuationHistoryResponse,
    PortfolioValuationResponse,
    PortfolioValuationSnapshotRead,
    PositionValuationResult,
)
from .service import (
    PortfolioNotFoundForValuationError,
    PositionNotFoundForValuationError,
    ValuationService,
)
from ..hardening.idempotency_service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyService,
)
from ..hardening.audit_service import AuditService
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops
from ..hardening.authorization.dependencies import (
    require_portfolio_access,
    require_position_portfolio_access,
)

router = APIRouter()
_service = ValuationService()
_idempotency = IdempotencyService()
_audit = AuditService()
_guard = require_admin_or_ops()


@router.get(
    "/portfolios/{portfolio_id}/valuation",
    response_model=PortfolioValuationResponse,
)
def get_portfolio_valuation(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        return _service.value_portfolio(db, portfolio_id)
    except PortfolioNotFoundForValuationError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/positions/{position_id}/valuation",
    response_model=PositionValuationResult,
)
def get_position_valuation(
    position_id: UUID,
    db: Session = Depends(get_db),
    _position=Depends(require_position_portfolio_access),
):
    try:
        return _service.value_position(db, position_id)
    except PositionNotFoundForValuationError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found",
        )


@router.post(
    "/portfolios/{portfolio_id}/valuation/snapshot",
    response_model=PortfolioValuationSnapshotRead,
    status_code=201,
)
def create_portfolio_valuation_snapshot(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    actor: ActorContext = Depends(_guard),
    _portfolio=Depends(require_portfolio_access),
):
    scope = f"valuation-snapshot:{portfolio_id}"
    request_data = {"portfolio_id": str(portfolio_id)}

    if idempotency_key:
        try:
            check = _idempotency.check_or_reserve(
                db, idempotency_key=idempotency_key, scope=scope,
                request_data=request_data,
            )
        except IdempotencyConflictError:
            raise HTTPException(status_code=409, detail="Idempotency key conflict: different payload")
        except IdempotencyInProgressError:
            raise HTTPException(status_code=409, detail="Request with this idempotency key is already in progress")
        if check.replayed:
            return JSONResponse(status_code=check.stored_status, content=check.stored_body)

    try:
        snapshot = _service.create_snapshot(db, portfolio_id)
        response_body = PortfolioValuationSnapshotRead.model_validate(snapshot).model_dump(mode="json")

        if idempotency_key:
            _idempotency.store_response(
                db, idempotency_key=idempotency_key, scope=scope,
                response_status=201, response_body=response_body,
            )

        _audit.log_success(
            db, entity_type="portfolio", entity_id=str(portfolio_id),
            action="valuation_snapshot_created", request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        db.commit()
        return snapshot
    except PortfolioNotFoundForValuationError:
        _audit.log_failure(
            db, entity_type="portfolio", entity_id=str(portfolio_id),
            action="valuation_snapshot_created", error="portfolio_not_found",
            request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/portfolios/{portfolio_id}/valuation/history",
    response_model=PortfolioValuationHistoryResponse,
)
def list_portfolio_valuation_history(
    portfolio_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        items, total = _service.list_snapshots(
            db, portfolio_id, skip=skip, limit=limit,
        )
    except PortfolioNotFoundForValuationError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return PortfolioValuationHistoryResponse(items=items, total=total)
