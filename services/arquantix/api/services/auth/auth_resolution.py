"""
Résolution auth à 3 niveaux (PR C / C.1) — sans modifier le format JWT.

- **jwt_only** : claims vérifiés + bundle cache absent + ``person_id`` dans le jeton — **aucune** requête DB
  pour résoudre ``AdminUser`` / ``Client`` (voir docstring :class:`FastIdentityResolution`).
- **cache** : bundle ``auth:user:{admin_user_id}`` TTL — **aucune** requête DB pour identité.
- **db** : ``_get_current_user_internal`` + warm cache (vérité serveur pour identité).

Les routes **refresh**, **revoke**, **custody**, opérations financières / sécurité : utiliser
``get_current_user_strict`` (auth) — pas le mode *fast* identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from uuid import UUID

from jose import JWTError, jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY, _get_current_user_internal
from database import AdminUser
from services.auth.auth_performance_metrics import (
    bump_auth_db_hit,
    bump_auth_jwt_only_hit,
    bump_auth_resolution_mode,
)
from services.auth.identity_cache import (
    USER_IDENTITY_CACHE_MISS,
    get_user_identity_cached,
    warm_identity_caches_from_user_db,
)


@dataclass(frozen=True)
class JwtAuthContext:
    """Contexte dérivé **uniquement** du JWT access vérifié (aucune DB)."""

    admin_user_id: int
    person_id: Optional[UUID]
    sid: Optional[str]
    raw_sub: str
    sub_typ: Optional[str]


@dataclass(frozen=True)
class FastIdentityResolution:
    """Résultat ``get_current_user_fast`` / ``resolve_identity_for_auth_context_fast``."""

    user_id: int
    email: Optional[str]
    person_id: Optional[UUID]
    client_id: Optional[UUID]
    zero_trust_role: str
    sub_typ: str
    resolution_mode: str  # jwt_only | cache | db


def decode_verified_access_payload(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def _parse_au_admin_id(sub_raw: str) -> Optional[int]:
    s = str(sub_raw or "").strip()
    if len(s) < 4 or not s.lower().startswith("au:"):
        return None
    rest = s[3:].strip()
    if not rest.isdigit():
        return None
    uid = int(rest)
    return uid if uid > 0 else None


def resolve_auth_context_jwt_only_from_payload(
    payload: dict, *, record_jwt_metric: bool = True
) -> JwtAuthContext:
    """LEVEL 1 — parse claims déjà décodés ; **aucune DB**."""
    sub_raw = payload.get("sub")
    uid = _parse_au_admin_id(str(sub_raw) if sub_raw is not None else "")
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    pid: Optional[UUID] = None
    raw_pid = payload.get("person_id") or payload.get("pid")
    if raw_pid:
        try:
            pid = UUID(str(raw_pid))
        except ValueError:
            pid = None
    sid = payload.get("sid")
    if record_jwt_metric:
        bump_auth_jwt_only_hit()
    return JwtAuthContext(
        admin_user_id=uid,
        person_id=pid,
        sid=str(sid) if sid else None,
        raw_sub=str(sub_raw).strip(),
        sub_typ=str(payload.get("sub_typ") or "") or None,
    )


def resolve_auth_context_jwt_only(token: str, *, record_jwt_metric: bool = True) -> JwtAuthContext:
    """
    LEVEL 1 — JWT uniquement (aucune DB).

    Lève ``HTTPException`` 401 si jeton invalide ou ``sub`` non canonique ``au:<id>``.
    """
    try:
        payload = decode_verified_access_payload(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return resolve_auth_context_jwt_only_from_payload(payload, record_jwt_metric=record_jwt_metric)


def resolve_identity_for_auth_context_fast(token: str, db: Session) -> FastIdentityResolution:
    """
    Résolution identity/KYC **rapide** (PR C.1) : bundle cache → sinon JWT ``person_id`` → sinon DB.

    **jwt_only** : cache miss et ``person_id`` présent dans le JWT — pas de lookup ``AdminUser`` /
    ``Client`` (``client_id`` peut être ``None`` jusqu’au prochain chargement DB).

    **cache** : bundle ``auth:user:{id}`` TTL.

    **db** : ``_get_current_user_internal`` + warm.
    """
    try:
        payload = decode_verified_access_payload(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_ctx = resolve_auth_context_jwt_only_from_payload(payload, record_jwt_metric=False)

    cached = get_user_identity_cached(jwt_ctx.admin_user_id)
    if cached is not USER_IDENTITY_CACHE_MISS:
        bump_auth_resolution_mode("cache")
        return FastIdentityResolution(
            user_id=jwt_ctx.admin_user_id,
            email=cached.email,
            person_id=cached.person_id,
            client_id=cached.client_id,
            zero_trust_role=cached.zero_trust_role,
            sub_typ="user_id",
            resolution_mode="cache",
        )

    if jwt_ctx.person_id is not None:
        bump_auth_resolution_mode("jwt_only")
        bump_auth_jwt_only_hit()
        return FastIdentityResolution(
            user_id=jwt_ctx.admin_user_id,
            email=None,
            person_id=jwt_ctx.person_id,
            client_id=None,
            zero_trust_role="admin",
            sub_typ="user_id",
            resolution_mode="jwt_only",
        )

    bump_auth_resolution_mode("db")
    bump_auth_db_hit()
    user, _er, _et, sub_typ = _get_current_user_internal(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    warm_identity_caches_from_user_db(db, user)
    ident = get_user_identity_cached(user.id)
    if ident is not USER_IDENTITY_CACHE_MISS:
        return FastIdentityResolution(
            user_id=user.id,
            email=ident.email,
            person_id=ident.person_id,
            client_id=ident.client_id,
            zero_trust_role=ident.zero_trust_role,
            sub_typ=sub_typ or "user_id",
            resolution_mode="db",
        )
    return FastIdentityResolution(
        user_id=user.id,
        email=user.email,
        person_id=user.person_id,
        client_id=None,
        zero_trust_role=getattr(user, "zero_trust_role", None) or "admin",
        sub_typ=sub_typ or "user_id",
        resolution_mode="db",
    )


def resolve_identity_for_auth_context_fast_with_client(
    token: str, db: Session
) -> FastIdentityResolution:
    """Alias : le bundle post-DB inclut déjà ``client_id`` lorsque disponible."""
    return resolve_identity_for_auth_context_fast(token, db)


def resolve_auth_context_with_cache(token: str, db: Session) -> Tuple[AdminUser, str]:
    """
    LEVEL 2 — DB : charge ``AdminUser`` + warm caches identité.

    Retourne ``(user, sub_typ)``.
    """
    bump_auth_db_hit()
    bump_auth_resolution_mode("db")
    user, _error_reason, _error_type, sub_typ = _get_current_user_internal(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    warm_identity_caches_from_user_db(db, user)
    return user, sub_typ or "user_id"


def resolve_auth_context_strict_db(token: str, db: Session) -> Tuple[AdminUser, str]:
    """LEVEL 3 — résolution stricte identique à *with_cache* (alias explicite)."""
    return resolve_auth_context_with_cache(token, db)
