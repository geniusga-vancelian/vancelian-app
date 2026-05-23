"""Endpoints **dev/test** pour lier Privy → Person sans SQL manuel (`/auth/privy/dev-*`)."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY
from database import Person, PersonExternalIdentity, get_db
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    DuplicateExternalIdentityError,
    get_pe_client_for_person,
    link_external_identity_to_person,
)
from services.auth.privy_dev_tools import ensure_privy_dev_tools_or_403

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-privy-dev"])
_optional_bearer = HTTPBearer(auto_error=False)


class PrivyDevLinkRequest(BaseModel):
    person_id: UUID
    privy_user_id: str = Field(..., min_length=1)
    email: Optional[str] = None


class PrivyDevLinkResponse(BaseModel):
    ok: bool
    idempotent: bool = False


class PrivyDevCurrentPersonResponse(BaseModel):
    person_id: str
    pe_client_id: Optional[str] = None
    jwt_subject: str


@router.post(
    "/privy/dev-link",
    response_model=PrivyDevLinkResponse,
    summary="[dev] Lier privy_user_id → person_id",
)
def post_privy_dev_link(
    request: Request,
    body: PrivyDevLinkRequest,
    db: Session = Depends(get_db),
) -> PrivyDevLinkResponse:
    ensure_privy_dev_tools_or_403(request)

    person = db.query(Person).filter(Person.id == body.person_id).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.dev_link_person_not_found",
                "message": "Person introuvable.",
            },
        )

    subj = body.privy_user_id.strip()
    if not subj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "privy.dev_link_invalid_privy_user_id",
                "message": "privy_user_id requis.",
            },
        )

    existing = (
        db.query(PersonExternalIdentity)
        .filter(
            PersonExternalIdentity.provider == PROVIDER_PRIVY,
            PersonExternalIdentity.external_subject == subj,
        )
        .first()
    )
    if existing is not None:
        if existing.person_id != body.person_id:
            logger.warning(
                "privy_dev_link_conflict",
                extra={
                    "event": "privy_dev_link_conflict",
                    "privy_prefix": subj[:48],
                    "existing_person_id": str(existing.person_id),
                    "requested_person_id": str(body.person_id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "privy.dev_link_conflict",
                    "message": "Ce privy_user_id est déjà lié à une autre personne.",
                },
            )
        link_external_identity_to_person(
            db,
            person_id=body.person_id,
            provider=PROVIDER_PRIVY,
            external_subject=subj,
            external_email=(body.email or "").strip() or None,
            external_phone=None,
            metadata_json=None,
        )
        db.commit()
        logger.info(
            "privy_dev_link_success",
            extra={
                "event": "privy_dev_link_success",
                "person_id": str(body.person_id),
                "privy_prefix": subj[:48],
                "idempotent": True,
            },
        )
        return PrivyDevLinkResponse(ok=True, idempotent=True)

    try:
        link_external_identity_to_person(
            db,
            person_id=body.person_id,
            provider=PROVIDER_PRIVY,
            external_subject=subj,
            external_email=(body.email or "").strip() or None,
            external_phone=None,
            metadata_json=None,
        )
        db.commit()
    except DuplicateExternalIdentityError as exc:
        logger.warning(
            "privy_dev_link_conflict",
            extra={
                "event": "privy_dev_link_conflict",
                "reason": str(exc),
                "privy_prefix": subj[:48],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "privy.dev_link_conflict",
                "message": str(exc),
            },
        ) from exc

    logger.info(
        "privy_dev_link_success",
        extra={
            "event": "privy_dev_link_success",
            "person_id": str(body.person_id),
            "privy_prefix": subj[:48],
            "idempotent": False,
        },
    )
    return PrivyDevLinkResponse(ok=True, idempotent=False)


@router.get(
    "/privy/dev-current-person",
    response_model=PrivyDevCurrentPersonResponse,
    summary="[dev] person_id depuis le JWT Vancelian courant",
)
def get_privy_dev_current_person(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
) -> PrivyDevCurrentPersonResponse:
    ensure_privy_dev_tools_or_403(request)

    if credentials is None or not (credentials.credentials or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.dev_current_person_requires_session",
                "message": "Authorization: Bearer avec JWT Vancelian requis.",
            },
        )

    token = credentials.credentials.strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.dev_current_person_requires_session",
                "message": "JWT invalide ou expiré.",
            },
        )

    raw_sub = str(payload.get("sub") or "").strip()
    if not raw_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.dev_current_person_requires_session",
                "message": "Claim sub manquant.",
            },
        )

    person_id_raw = payload.get("person_id")
    if person_id_raw is None or str(person_id_raw).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.dev_current_person_requires_session",
                "message": "Claim person_id manquant dans le JWT.",
            },
        )

    try:
        pid = UUID(str(person_id_raw).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.dev_current_person_requires_session",
                "message": "person_id JWT invalide.",
            },
        ) from exc

    pe_client = get_pe_client_for_person(db, person_id=pid)
    return PrivyDevCurrentPersonResponse(
        person_id=str(pid),
        pe_client_id=str(pe_client.id) if pe_client is not None else None,
        jwt_subject=raw_sub,
    )
