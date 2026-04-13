"""Rebalance Preview API endpoints (Portfolio Engine — simulation only).

Standalone endpoints: POST, GET/{id}.
Nested endpoints in the portfolios router:
  GET /portfolios/{id}/rebalance-preview/latest
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from .schemas import PreviewCreate, PreviewRead
from .service import (
    InstrumentReferenceError,
    PolicyReferenceError,
    PortfolioReferenceError,
    PreviewNotFoundError,
    RebalancePreviewService,
)
from ..hardening.idempotency_service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyService,
)
from ..hardening.audit_service import AuditService
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import get_actor_context, require_admin_or_ops
from ..hardening.authorization.service import AuthorizationService

router = APIRouter()

_service = RebalancePreviewService()
_idempotency = IdempotencyService()
_audit = AuditService()
_guard = require_admin_or_ops()
_authz = AuthorizationService()


@router.post("", response_model=PreviewRead, status_code=status.HTTP_201_CREATED)
def create_preview(
    payload: PreviewCreate,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    actor: ActorContext = Depends(_guard),
):
    if not _authz.can_access_portfolio(db, actor, payload.portfolio_id):
        raise HTTPException(status_code=403, detail="Forbidden: insufficient access to this portfolio")

    scope = f"rebalance-plan:{payload.portfolio_id}"
    request_data = payload.model_dump(mode="json")

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
        preview = _service.create_preview(db, payload)
        db.commit()
        db.refresh(preview)
        result = PreviewRead.model_validate(preview)
        response_body = result.model_dump(mode="json")

        if idempotency_key:
            _idempotency.store_response(
                db, idempotency_key=idempotency_key, scope=scope,
                response_status=201, response_body=response_body,
            )
            db.commit()

        _audit.log_success(
            db, entity_type="portfolio", entity_id=str(payload.portfolio_id),
            action="rebalance_plan_created", request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        db.commit()
        return result
    except (PortfolioReferenceError, PolicyReferenceError, InstrumentReferenceError) as exc:
        _audit.log_failure(
            db, entity_type="portfolio", entity_id=str(payload.portfolio_id),
            action="rebalance_plan_created", error=str(exc),
            request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{preview_id}", response_model=PreviewRead)
def get_preview(
    preview_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        preview = _service.get_preview(db, preview_id)
        return PreviewRead.model_validate(preview)
    except PreviewNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RebalancePreview not found")
