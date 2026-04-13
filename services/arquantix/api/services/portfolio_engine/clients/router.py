"""Clients API endpoints (Portfolio Engine — ownership layer)."""
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import AdminUser, get_db
from .repository import DuplicateEmailError
from .schemas import ClientCreate, ClientListResponse, ClientRead, ClientUpdate
from .service import ClientNotFoundError, ClientService
from services.auth.dependencies import require_client_access_identity
from services.auth.models import AuthContext
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action

router = APIRouter()

_service = ClientService()


class ClientIdentityResponse(BaseModel):
    person: Optional[Dict[str, Any]] = None
    client: Optional[Dict[str, Any]] = None
    jurisdiction: Optional[str] = None
    kyc_status: Optional[str] = None
    is_linked: bool = False


@router.get("", response_model=ClientListResponse)
def list_clients(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_clients(db, status=status_filter, skip=skip, limit=limit)
    return ClientListResponse(
        items=[ClientRead.model_validate(c) for c in items],
        total=total,
    )


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        client = _service.create_client(db, payload)
        db.commit()
        db.refresh(client)
        return ClientRead.model_validate(client)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        client = _service.get_client(db, client_id)
        return ClientRead.model_validate(client)
    except ClientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        client = _service.update_client(db, client_id, payload)
        db.commit()
        db.refresh(client)
        return ClientRead.model_validate(client)
    except ClientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{client_id}/identity", response_model=ClientIdentityResponse)
def get_client_identity(
    client_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_client_access_identity),
    _continuous_auth: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
):
    """Get consolidated identity view from a client_id."""
    from services.client_identity.service import (
        ClientIdentityService,
        ClientNotFoundError as IdentityClientNotFoundError,
    )
    _ = _continuous_auth
    dev = (request.headers.get("x-device-id") or "")[:128]
    try:
        identity = ClientIdentityService.get_client_identity_by_client_id(db, client_id)
        resp = ClientIdentityResponse(**identity)
        record_sensitive_action_completed(
            user_id=auth.user_id,
            action_key="view_sensitive_data",
            request=request,
            db=db,
            device_id=dev,
            extra={
                "endpoint": "GET /api/portfolio-engine/clients/{client_id}/identity",
                "data_scope": "kyc",
                "client_id": str(client_id),
                "sensitive_fields_accessed": ["person", "client"],
            },
        )
        db.commit()
        return resp
    except IdentityClientNotFoundError:
        record_sensitive_action_failed(
            user_id=auth.user_id,
            action_key="view_sensitive_data",
            request=request,
            db=db,
            device_id=dev,
            reason="client_not_found",
            extra={"client_id": str(client_id), "data_scope": "kyc"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
