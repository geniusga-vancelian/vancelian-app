"""Liaison Privy ↔ Person pour session Vancelian authentifiée (prod / staging).

Contrairement à ``/auth/privy/dev-link``, le ``person_id`` est tiré **uniquement**
du JWT (claim ``person_id``) : le client envoie seulement ``privy_user_id``.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY
from database import Person, PersonExternalIdentity, get_db
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    DuplicateExternalIdentityError,
    link_external_identity_to_person,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-privy"])
_bearer_required = HTTPBearer(auto_error=False)


class PrivyLinkRequest(BaseModel):
    privy_user_id: str = Field(..., min_length=1)
    email: Optional[str] = None


class PrivyLinkResponse(BaseModel):
    ok: bool
    idempotent: bool = False


def _jwt_person_uuid(token: str) -> UUID:
    try:
        payload = jwt.decode(token.strip(), SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.link_invalid_session",
                "message": "JWT invalide ou expiré.",
            },
        ) from exc

    person_id_raw = payload.get("person_id")
    if person_id_raw is None or str(person_id_raw).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.link_requires_person_claim",
                "message": "Claim person_id manquant dans le JWT.",
            },
        )
    try:
        return UUID(str(person_id_raw).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.link_requires_person_claim",
                "message": "person_id JWT invalide.",
            },
        ) from exc


@router.post(
    "/privy/link",
    response_model=PrivyLinkResponse,
    summary="Lier privy_user_id au person_id dérivé du JWT Vancelian",
)
def post_privy_link_authenticated_session(
    body: PrivyLinkRequest,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_required),
) -> PrivyLinkResponse:
    if credentials is None or not (credentials.credentials or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.link_requires_session",
                "message": "Authorization: Bearer (JWT Vancelian) requis.",
            },
        )

    pid = _jwt_person_uuid(credentials.credentials)
    person = db.query(Person).filter(Person.id == pid).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.link_person_not_found",
                "message": "Person introuvable.",
            },
        )

    subj = body.privy_user_id.strip()
    if not subj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "privy.link_invalid_privy_user_id",
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
        if existing.person_id != pid:
            logger.warning(
                "privy_link_conflict",
                extra={
                    "event": "privy_link_conflict",
                    "privy_prefix": subj[:48],
                    "existing_person_id": str(existing.person_id),
                    "requested_person_id": str(pid),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "privy.link_conflict",
                    "message": "Ce privy_user_id est déjà lié à une autre personne.",
                },
            )
        link_external_identity_to_person(
            db,
            person_id=pid,
            provider=PROVIDER_PRIVY,
            external_subject=subj,
            external_email=(body.email or "").strip() or None,
            external_phone=None,
            metadata_json=None,
        )
        db.commit()
        logger.info(
            "privy_link_success",
            extra={
                "event": "privy_link_success",
                "person_id": str(pid),
                "privy_prefix": subj[:48],
                "idempotent": True,
            },
        )
        return PrivyLinkResponse(ok=True, idempotent=True)

    try:
        link_external_identity_to_person(
            db,
            person_id=pid,
            provider=PROVIDER_PRIVY,
            external_subject=subj,
            external_email=(body.email or "").strip() or None,
            external_phone=None,
            metadata_json=None,
        )
        db.commit()
    except DuplicateExternalIdentityError as exc:
        logger.warning(
            "privy_link_conflict",
            extra={
                "event": "privy_link_conflict",
                "reason": str(exc),
                "privy_prefix": subj[:48],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "privy.link_conflict",
                "message": str(exc),
            },
        ) from exc

    logger.info(
        "privy_link_success",
        extra={
            "event": "privy_link_success",
            "person_id": str(pid),
            "privy_prefix": subj[:48],
            "idempotent": False,
        },
    )
    return PrivyLinkResponse(ok=True, idempotent=False)
