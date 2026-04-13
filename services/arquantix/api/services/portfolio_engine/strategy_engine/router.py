"""FastAPI router for the Strategy Engine (Phase 7).

Endpoints nested under /portfolios/ and /strategy-engine/.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from .schemas import (
    PortfolioEvaluationResponse,
    StrategySignalListResponse,
    StrategyEvaluationLogRead,
)
from .service import (
    StrategyEngineService,
    PortfolioNotFoundForStrategyError,
    StrategyInstanceNotFoundError,
)
from ..hardening.idempotency_service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyService,
)
from ..hardening.audit_service import AuditService
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops
from ..hardening.authorization.dependencies import require_portfolio_access

router = APIRouter()
_service = StrategyEngineService()
_idempotency = IdempotencyService()
_audit = AuditService()
_guard = require_admin_or_ops()


@router.post(
    "/portfolios/{portfolio_id}/strategy-evaluation",
    response_model=PortfolioEvaluationResponse,
    status_code=200,
)
def evaluate_portfolio_strategies(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    actor: ActorContext = Depends(_guard),
    _portfolio=Depends(require_portfolio_access),
):
    scope = f"strategy-evaluation:{portfolio_id}"
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
        result = _service.evaluate_portfolio_strategies(db, portfolio_id)
        response_body = result.model_dump(mode="json")

        if idempotency_key:
            _idempotency.store_response(
                db, idempotency_key=idempotency_key, scope=scope,
                response_status=200, response_body=response_body,
            )

        _audit.log_success(
            db, entity_type="portfolio", entity_id=str(portfolio_id),
            action="strategy_evaluated", request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        db.commit()
        return result
    except PortfolioNotFoundForStrategyError:
        _audit.log_failure(
            db, entity_type="portfolio", entity_id=str(portfolio_id),
            action="strategy_evaluated", error="portfolio_not_found",
            request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/portfolios/{portfolio_id}/strategy-signals",
    response_model=StrategySignalListResponse,
)
def list_strategy_signals(
    portfolio_id: UUID,
    signal_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    from .repository import StrategyEvaluationRepository

    repo = StrategyEvaluationRepository()
    items, total = repo.list_by_portfolio(
        db, portfolio_id, signal_type=signal_type, skip=skip, limit=limit,
    )
    return StrategySignalListResponse(
        items=[StrategyEvaluationLogRead.model_validate(e) for e in items],
        total=total,
    )


@router.post(
    "/strategy-engine/{strategy_instance_id}/execute",
    response_model=PortfolioEvaluationResponse,
    status_code=200,
)
def execute_strategy_action(
    strategy_instance_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        result = _service.execute_strategy_action(db, strategy_instance_id)
        db.commit()
        return result
    except StrategyInstanceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"StrategyInstance {strategy_instance_id} not found",
        )
