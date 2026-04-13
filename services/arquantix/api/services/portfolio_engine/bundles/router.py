"""Bundle Engine v1 — FastAPI router.

Endpoints:
  POST   /admin/bundles                   — create bundle (idempotent, RBAC admin/ops)
  GET    /admin/bundles                   — list bundles (RBAC admin/ops)
  GET    /admin/bundles/{id}              — bundle detail (RBAC admin/ops)
  PATCH  /admin/bundles/{id}/visibility   — publish/unpublish (RBAC admin/ops, audited)
  DELETE /admin/bundles/{id}              — delete bundle (RBAC admin/ops, blocked if subscriptions)

Transaction strategy:
  - Success: service flushes → router commits
  - Failure: router rollbacks → failure audit in separate session
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from ..hardening.audit_service import AuditService
from ..hardening.idempotency_service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyService,
)
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import get_actor_context, require_admin_or_ops
from .schemas import (
    BundleCreate,
    BundleDetailResponse,
    BundleListResponse,
    BundleVisibilityResponse,
    BundleVisibilityUpdate,
)
from .service import (
    BundleEngineService,
    BundleHasSubscriptionsError,
    BundleNotFoundError,
    BundleValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter()
_svc = BundleEngineService()
_guard = require_admin_or_ops()

IDEMPOTENCY_SCOPE = "bundle_create"


def _log_failure_audit_separate_session(
    *,
    product_code: str,
    error_msg: str,
    actor_type: str,
    actor_id: Optional[str],
    request_id: Optional[str],
    action: str = "bundle_created",
) -> None:
    """Best-effort failure audit in a dedicated session that survives rollback."""
    audit_db: Optional[Session] = None
    try:
        audit_db = SessionLocal()
        AuditService.log_failure(
            audit_db,
            entity_type="bundle",
            entity_id=product_code,
            action=action,
            error=error_msg,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            metadata={"product_code": product_code},
        )
        audit_db.commit()
    except Exception:
        logger.exception(
            "Failed to persist failure audit event for %s: %s",
            action,
            product_code,
        )
    finally:
        if audit_db is not None:
            audit_db.close()


@router.post(
    "/bundles",
    response_model=BundleDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bundle product",
)
def create_bundle(
    payload: BundleCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    actor_type = actor.actor_type
    actor_id = actor.actor_id
    product_code = payload.product_code

    # ── Idempotency check ──
    if idempotency_key:
        scope_key = f"{IDEMPOTENCY_SCOPE}:{product_code}"
        try:
            result = IdempotencyService.check_or_reserve(
                db,
                idempotency_key=idempotency_key,
                scope=scope_key,
                request_data=payload.model_dump(mode="json"),
            )
            if result.replayed:
                return BundleDetailResponse(**result.stored_body)
        except IdempotencyConflictError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency key '{idempotency_key}' already used with a different payload",
            )
        except IdempotencyInProgressError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Request with idempotency key '{idempotency_key}' is already being processed",
            )

    # ── Create bundle (transactional) ──
    try:
        response = _svc.create_bundle(
            db,
            payload,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=x_request_id,
        )

        # Store idempotency response before commit
        if idempotency_key:
            scope_key = f"{IDEMPOTENCY_SCOPE}:{product_code}"
            IdempotencyService.store_response(
                db,
                idempotency_key=idempotency_key,
                scope=scope_key,
                response_status=201,
                response_body=response.model_dump(mode="json"),
            )

        db.commit()
        return response

    except BundleValidationError as exc:
        db.rollback()
        _log_failure_audit_separate_session(
            product_code=product_code,
            error_msg=str(exc),
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=x_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except ValidationError as exc:
        db.rollback()
        _log_failure_audit_separate_session(
            product_code=product_code,
            error_msg=str(exc),
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=x_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.exception("Bundle creation failed for %s", product_code)
        _log_failure_audit_separate_session(
            product_code=product_code,
            error_msg=error_msg,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=x_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bundle creation failed unexpectedly",
        )


@router.get(
    "/bundles",
    response_model=BundleListResponse,
    summary="List all bundle products",
)
def list_bundles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    return _svc.list_bundles(db, skip=skip, limit=limit)


@router.get(
    "/bundles/{bundle_id}",
    response_model=BundleDetailResponse,
    summary="Get bundle detail by product ID",
)
def get_bundle(
    bundle_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        return _svc.get_bundle(db, bundle_id)
    except BundleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )


@router.patch(
    "/bundles/{bundle_id}/visibility",
    response_model=BundleVisibilityResponse,
    summary="Publish or unpublish a bundle",
)
def set_bundle_visibility(
    bundle_id: UUID,
    payload: BundleVisibilityUpdate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    try:
        result = _svc.set_visibility(
            db,
            bundle_id,
            is_public=payload.is_public,
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            request_id=x_request_id,
        )
        db.commit()
        return result

    except BundleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )

    except Exception as exc:
        db.rollback()
        action = "bundle_published" if payload.is_public else "bundle_unpublished"
        logger.exception("Bundle visibility update failed for %s", bundle_id)
        _log_failure_audit_separate_session(
            product_code=str(bundle_id),
            error_msg=f"{type(exc).__name__}: {exc}",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            request_id=x_request_id,
            action=action,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Visibility update failed unexpectedly",
        )


@router.delete(
    "/bundles/{bundle_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a bundle (blocked if active subscriptions exist)",
)
def delete_bundle(
    bundle_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    try:
        result = _svc.delete_bundle(
            db,
            bundle_id,
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            request_id=x_request_id,
        )
        db.commit()
        return result

    except BundleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )

    except BundleHasSubscriptionsError as exc:
        _log_failure_audit_separate_session(
            product_code=str(bundle_id),
            error_msg=str(exc),
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            request_id=x_request_id,
            action="bundle_delete_denied",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()
        logger.exception("Bundle deletion failed for %s", bundle_id)
        _log_failure_audit_separate_session(
            product_code=str(bundle_id),
            error_msg=f"{type(exc).__name__}: {exc}",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            request_id=x_request_id,
            action="bundle_deleted",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bundle deletion failed unexpectedly",
        )
