"""FastAPI router for the Rebalance Orchestrator (Phase 8)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action
from .schemas import (
    OrchestrationResult,
    OrchestrationRunListResponse,
    OrchestrationRunRead,
)
from .service import (
    OrchestrationRunNotFoundError,
    PortfolioNotFoundForOrchestrationError,
    RebalanceOrchestratorService,
)
from .repository import OrchestrationRunRepository
from ..hardening.idempotency_service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyService,
)
from ..hardening.audit_service import AuditService
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import get_actor_context, require_admin_or_ops
from ..hardening.authorization.dependencies import (
    require_orchestration_run_portfolio_access,
    require_portfolio_access,
)

router = APIRouter()
_service = RebalanceOrchestratorService()
_repo = OrchestrationRunRepository()
_idempotency = IdempotencyService()
_audit = AuditService()
_guard = require_admin_or_ops()


def _dev(request: Request) -> str:
    return (request.headers.get("x-device-id") or "")[:128]


@router.post(
    "/portfolios/{portfolio_id}/orchestrate",
    response_model=OrchestrationResult,
    status_code=200,
)
def run_orchestration(
    request: Request,
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    actor: ActorContext = Depends(_guard),
    _portfolio=Depends(require_portfolio_access),
):
    _ = current_user
    scope = f"orchestrate:{portfolio_id}"
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
            record_sensitive_action_completed(
                user_id=current_user.id,
                action_key="wallet_transfer",
                request=request,
                db=db,
                device_id=_dev(request),
                extra={
                    "endpoint": "POST /api/portfolio-engine/portfolios/{id}/orchestrate",
                    "portfolio_id": str(portfolio_id),
                    "replayed": True,
                    "idempotency_key": (idempotency_key or "")[:128],
                },
            )
            db.commit()
            return JSONResponse(status_code=check.stored_status, content=check.stored_body)

    try:
        result = _service.run_portfolio_cycle(db, portfolio_id)
        response_body = result.model_dump(mode="json")

        if idempotency_key:
            _idempotency.store_response(
                db, idempotency_key=idempotency_key, scope=scope,
                response_status=200, response_body=response_body,
            )

        _audit.log_success(
            db, entity_type="portfolio", entity_id=str(portfolio_id),
            action="orchestrated", request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/portfolio-engine/portfolios/{id}/orchestrate",
                "portfolio_id": str(portfolio_id),
            },
        )
        db.commit()
        return result
    except PortfolioNotFoundForOrchestrationError:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="portfolio_not_found",
            extra={"portfolio_id": str(portfolio_id)},
        )
        _audit.log_failure(
            db, entity_type="portfolio", entity_id=str(portfolio_id),
            action="orchestrated", error="portfolio_not_found",
            request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/portfolios/{portfolio_id}/orchestration-runs",
    response_model=OrchestrationRunListResponse,
)
def list_orchestration_runs(
    portfolio_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    items, total = _repo.list_by_portfolio(db, portfolio_id, skip=skip, limit=limit)
    return OrchestrationRunListResponse(
        items=[OrchestrationRunRead.model_validate(r) for r in items],
        total=total,
    )


@router.get(
    "/orchestration-runs/{run_id}",
    response_model=OrchestrationRunRead,
)
def get_orchestration_run(
    run_id: UUID,
    _run=Depends(require_orchestration_run_portfolio_access),
):
    return OrchestrationRunRead.model_validate(_run)
