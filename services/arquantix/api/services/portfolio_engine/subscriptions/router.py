"""Subscriptions API endpoints (Portfolio Engine — product subscription layer)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from ..portfolios.schemas import PortfolioRead
from ..provisioning.errors import (
    AlreadyProvisionedError,
    ClientNotEligibleError,
    InactiveProductError,
    InvalidSubscriptionStateError,
    ProvisioningSubscriptionNotFoundError,
    ProvisioningTemplateNotFoundError,
    TemplateProductMismatchError,
)
from ..provisioning.service import ProvisioningService
from .schemas import ProvisionRequest, SubscriptionCreate, SubscriptionListResponse, SubscriptionRead, SubscriptionUpdate
from .service import (
    ClientReferenceError,
    PortfolioReferenceError,
    ProductNotAvailableError,
    ProductReferenceError,
    SubscriptionNotFoundError,
    SubscriptionService,
)
from ..hardening.idempotency_service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyService,
)
from ..hardening.audit_service import AuditService
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import require_admin_or_ops

router = APIRouter()

_service = SubscriptionService()
_provisioning = ProvisioningService()
_idempotency = IdempotencyService()
_audit = AuditService()
_guard = require_admin_or_ops()


@router.get("", response_model=SubscriptionListResponse)
def list_subscriptions(
    client_id: Optional[UUID] = Query(None, description="Filter by client_id"),
    product_id: Optional[UUID] = Query(None, description="Filter by product_id"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_subscriptions(
        db,
        client_id=client_id,
        product_id=product_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return SubscriptionListResponse(
        items=[SubscriptionRead.model_validate(s) for s in items],
        total=total,
    )


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
):
    try:
        subscription = _service.create_subscription(db, payload)
        db.commit()
        db.refresh(subscription)
        return SubscriptionRead.model_validate(subscription)
    except ProductNotAvailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except (ClientReferenceError, ProductReferenceError, PortfolioReferenceError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{subscription_id}", response_model=SubscriptionRead)
def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        subscription = _service.get_subscription(db, subscription_id)
        return SubscriptionRead.model_validate(subscription)
    except SubscriptionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProductSubscription not found")


@router.patch("/{subscription_id}", response_model=SubscriptionRead)
def update_subscription(
    subscription_id: UUID,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
):
    try:
        subscription = _service.update_subscription(db, subscription_id, payload)
        db.commit()
        db.refresh(subscription)
        return SubscriptionRead.model_validate(subscription)
    except SubscriptionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProductSubscription not found")
    except PortfolioReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/{subscription_id}/provision", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def provision_subscription(
    subscription_id: UUID,
    payload: ProvisionRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    actor: ActorContext = Depends(_guard),
):
    scope = f"provision:{subscription_id}"
    request_data = {"subscription_id": str(subscription_id), "template_id": str(payload.template_id)}

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
        portfolio = _provisioning.provision_from_subscription(db, subscription_id, payload.template_id)
        result = PortfolioRead.model_validate(portfolio)
        response_body = result.model_dump(mode="json")

        if idempotency_key:
            _idempotency.store_response(
                db, idempotency_key=idempotency_key, scope=scope,
                response_status=201, response_body=response_body,
            )

        _audit.log_success(
            db, entity_type="subscription", entity_id=str(subscription_id),
            action="provisioned", request_id=x_request_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id,
            metadata={"template_id": str(payload.template_id)},
        )
        db.commit()
        return result
    except ProvisioningSubscriptionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProductSubscription not found")
    except ProvisioningTemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PortfolioTemplate not found")
    except InvalidSubscriptionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except AlreadyProvisionedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except TemplateProductMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except InactiveProductError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
