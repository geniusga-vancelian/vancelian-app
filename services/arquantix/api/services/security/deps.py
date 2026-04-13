"""Resolve authenticated person_id for 2FA endpoints."""
from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY
from database import Person, get_db

_bearer = HTTPBearer(auto_error=False)

TWO_FACTOR_REQUIRE_AUTH = os.getenv("TWO_FACTOR_REQUIRE_AUTH", "true").lower() in ("1", "true", "yes")


def _person_from_jwt(token: str, db: Session) -> Optional[UUID]:
    from services.auth.auth_performance_metrics import bump_auth_jwt_only_hit
    from services.auth.jwt_subject_resolution import NonUserJWTSubjectError, resolve_user_from_jwt_sub

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    pid = payload.get("person_id") or payload.get("pid")
    if pid:
        try:
            uid = UUID(str(pid))
            bump_auth_jwt_only_hit()
            return uid
        except ValueError:
            return None
    sub = payload.get("sub")
    if not sub:
        return None
    sub_s = str(sub).strip()
    if not sub_s:
        return None
    try:
        user, _st, kind = resolve_user_from_jwt_sub(db, sub_s, record_metric=False)
        if kind == "ok" and user is not None and user.person_id is not None:
            return user.person_id
    except NonUserJWTSubjectError:
        return None
    except Exception:
        return None
    return None


def resolve_person_id(
    person_id_body: Optional[UUID],
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
    *,
    anti_enum_missing_person: bool = False,
) -> UUID:
    """person_id from JWT; optional body must match when both present.

    If TWO_FACTOR_REQUIRE_AUTH=false (dev only), body person_id alone is accepted.

    When anti_enum_missing_person=True (2FA routes), unknown person returns 403 with a generic payload.
    """
    token_pid: Optional[UUID] = None
    if credentials and credentials.credentials:
        token_pid = _person_from_jwt(credentials.credentials, db)

    if token_pid is not None:
        if person_id_body is not None and person_id_body != token_pid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "unauthorized_2fa_request",
                    "message": "Unable to complete this request.",
                },
            )
        resolved = token_pid
    elif person_id_body is not None and not TWO_FACTOR_REQUIRE_AUTH:
        resolved = person_id_body
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    person = db.query(Person).filter(Person.id == resolved).first()
    if person is None:
        if anti_enum_missing_person:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "unauthorized_2fa_request",
                    "message": "Unable to complete this request.",
                },
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return resolved


def get_effective_person_id(
    person_id_query: Optional[UUID],
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> UUID:
    return resolve_person_id(person_id_query, credentials, db)
