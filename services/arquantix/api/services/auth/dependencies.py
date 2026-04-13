"""FastAPI dependencies for identity/KYC endpoint auth.

PR C.1 :
- ``get_current_user_fast`` / ``get_current_user_or_admin`` : bundle ``auth:user:`` → JWT ``person_id`` → DB.
- ``get_current_user_or_admin_strict`` : toujours ``_get_current_user_internal`` (vérité serveur).
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from services.auth.auth_resolution import (
    resolve_auth_context_strict_db,
    resolve_identity_for_auth_context_fast_with_client,
)
from services.auth.jwt_subject_resolution import classify_sub_format
from .models import AuthContext

logger = logging.getLogger(__name__)

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _get_jwt_settings():
    """Lazy import to avoid circular dependency with auth.py env loading."""
    from auth import SECRET_KEY, ALGORITHM
    return SECRET_KEY, ALGORITHM


def get_current_user_fast(
    request: Request,
    token: Optional[str] = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> AuthContext:
    """JWT + résolution identity rapide (cache / JWT-only / DB) — sans lookup DB systématique."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    secret, algorithm = _get_jwt_settings()

    r = resolve_identity_for_auth_context_fast_with_client(token, db)
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub_raw = payload.get("sub")
    if sub_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing identity claim",
        )

    jwt_sub_typ = r.sub_typ if r.sub_typ == "user_id" else None
    if jwt_sub_typ:
        sr = str(sub_raw)[:128]
        logger.debug(
            "jwt_subject_resolution",
            extra={
                "sub": sr,
                "sub_typ": jwt_sub_typ,
                "sub_format": classify_sub_format(sr),
                "resolved_user_id": r.user_id,
                "route": request.url.path,
            },
        )

    logger.debug(
        "auth_identity_resolution",
        extra={
            "auth_resolution_mode": r.resolution_mode,
            "route": request.url.path,
        },
    )

    from services.auth.device_pr_d4_policy import enforce_jwt_device_binding_if_configured

    enforce_jwt_device_binding_if_configured(token=token, x_device_id=x_device_id)

    return AuthContext(
        user_id=r.user_id,
        email=r.email,
        role="admin",
        zero_trust_role=r.zero_trust_role or "admin",
        person_id=r.person_id,
        client_id=r.client_id,
        jwt_sub_typ=jwt_sub_typ,
    )


def get_current_user_or_admin(
    request: Request,
    token: Optional[str] = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Alias : mode *fast* (PR C.1). Pour vérité DB à chaque requête, voir ``get_current_user_or_admin_strict``."""
    return get_current_user_fast(request=request, token=token, db=db)


def get_current_user_or_admin_strict(
    request: Request,
    token: Optional[str] = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> AuthContext:
    """Toujours ``resolve_auth_context_strict_db`` + enrichissement ``Client`` (comportement pré–PR C.1)."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    secret, algorithm = _get_jwt_settings()

    user, sub_typ = resolve_auth_context_strict_db(token, db)
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub_raw = payload.get("sub")
    if sub_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing identity claim",
        )

    jwt_sub_typ = sub_typ if sub_typ == "user_id" else None
    if jwt_sub_typ:
        sr = str(sub_raw)[:128]
        logger.debug(
            "jwt_subject_resolution",
            extra={
                "sub": sr,
                "sub_typ": jwt_sub_typ,
                "sub_format": classify_sub_format(sr),
                "resolved_user_id": user.id,
                "route": request.url.path,
            },
        )

    logger.debug(
        "auth_identity_resolution",
        extra={"auth_resolution_mode": "db", "route": request.url.path},
    )

    from services.auth.device_pr_d4_policy import enforce_jwt_device_binding_if_configured

    enforce_jwt_device_binding_if_configured(token=token, x_device_id=x_device_id)

    person_id = None
    client_id = None
    try:
        if user.person_id is not None:
            from services.auth.identity_cache import get_client_id_for_person_cached

            cid = get_client_id_for_person_cached(db, user.person_id)
            if cid is not None:
                client_id = cid
                person_id = user.person_id
    except Exception:
        pass

    return AuthContext(
        user_id=user.id,
        email=user.email,
        role="admin",
        zero_trust_role=getattr(user, "zero_trust_role", None) or "admin",
        person_id=person_id,
        client_id=client_id,
        jwt_sub_typ=jwt_sub_typ,
    )


def require_person_access(
    person_id: UUID,
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> AuthContext:
    """Ensure the current user owns this person or is admin."""
    if auth.is_admin:
        return auth
    if auth.person_id is not None and auth.person_id == person_id:
        return auth
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: you do not own this resource",
    )


def require_client_access_identity(
    client_id: UUID,
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> AuthContext:
    """Ensure the current user owns this client or is admin."""
    if auth.is_admin:
        return auth
    if auth.client_id is not None and auth.client_id == client_id:
        return auth
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: you do not own this resource",
    )


def require_admin(
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> AuthContext:
    """Only admin users may call this endpoint."""
    if not auth.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return auth


def get_current_user_or_legacy(
    request: Request,
    token: Optional[str] = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[AuthContext]:
    """Return AuthContext if a valid JWT is present, or None for legacy
    unauthenticated access (controlled by ALLOW_LEGACY_UNAUTHENTICATED_KYC).

    Phase 4C: utilisé uniquement par les endpoints legacy ``GET/POST /api/persons/{id}``
    (dépréciés). Ne pas réutiliser pour de nouvelles routes — préférer
    ``get_current_user_or_admin`` + garde-fous Zero Trust / auth continue.

    - If token present + valid → returns AuthContext
    - If token present + invalid → 401
    - If token absent + legacy flag ON → returns None (caller must log WARNING)
    - If token absent + legacy flag OFF → 401
    """
    if token is None:
        from core.env import allow_legacy_unauthenticated_kyc
        if allow_legacy_unauthenticated_kyc():
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_current_user_fast(request=request, token=token, db=db)
