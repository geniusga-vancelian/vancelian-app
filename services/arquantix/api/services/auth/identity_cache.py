"""Cache TTL mémoire pour identifiants peu volatils — PR C / C.1.

Clé canonique : ``auth:user:{admin_user_id}`` → :class:`CachedUserIdentity` (person_id, client_id, email, …).

Clés legacy ``auth:admin_user_person:`` / ``auth:person_client:`` restent synchronisées au write pour compatibilité.

Ne pas y placer de secrets, tokens, ni états sécurité dynamiques (lock, step-up).
Invalidation : TTL uniquement (pas d’invalidation croisée).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from database import AdminUser
from services.auth.redis_client import get_redis_client
from services.auth.redis_metrics import bump_redis_error, bump_redis_hit, bump_redis_miss
from services.security.security_env import is_redis_cache_enabled

logger = logging.getLogger("arquantix.auth.identity_cache")

_lock = threading.Lock()
_store: dict[str, tuple[Any, float]] = {}

_DEFAULT_TTL = int(os.getenv("AUTH_IDENTITY_CACHE_TTL_SECONDS", "900"))
# PR C.1 : 5–15 min pour le bundle utilisateur (person + client + email)
_USER_BUNDLE_TTL = int(os.getenv("AUTH_USER_IDENTITY_CACHE_TTL_SECONDS", "600"))


class PersonIdCacheMiss:
    """Sentinel : aucune entrée TTL valide pour cet ``admin_user_id``."""


PERSON_ID_CACHE_MISS = PersonIdCacheMiss()


class UserIdentityCacheMiss:
    """Sentinel : pas de bundle ``auth:user:{id}`` valide."""


USER_IDENTITY_CACHE_MISS = UserIdentityCacheMiss()


@dataclass(frozen=True)
class CachedUserIdentity:
    """Snapshot identité servi depuis le cache (pas l’autorité sécurité temps réel)."""

    person_id: Optional[UUID]
    client_id: Optional[UUID]
    email: Optional[str] = None
    zero_trust_role: str = "admin"


def _now() -> float:
    return time.monotonic()


def _purge_expired() -> None:
    t = _now()
    dead = [k for k, (_, exp) in _store.items() if exp <= t]
    for k in dead:
        _store.pop(k, None)


def _key_user_bundle(admin_user_id: int) -> str:
    return f"auth:user:{admin_user_id}"


def _key_person_by_user(admin_user_id: int) -> str:
    return f"auth:admin_user_person:{admin_user_id}"


def _key_client_by_person(person_id: UUID) -> str:
    return f"auth:person_client:{person_id}"


def _identity_to_json(ident: CachedUserIdentity) -> str:
    return json.dumps(
        {
            "person_id": str(ident.person_id) if ident.person_id is not None else None,
            "client_id": str(ident.client_id) if ident.client_id is not None else None,
            "email": ident.email,
            "zero_trust_role": ident.zero_trust_role,
        },
        separators=(",", ":"),
    )


def _identity_from_json(raw: str) -> CachedUserIdentity:
    d = json.loads(raw)
    pid = UUID(d["person_id"]) if d.get("person_id") else None
    cid = UUID(d["client_id"]) if d.get("client_id") else None
    return CachedUserIdentity(
        person_id=pid,
        client_id=cid,
        email=d.get("email"),
        zero_trust_role=(d.get("zero_trust_role") or "admin"),
    )


def get_ttl_seconds() -> int:
    """TTL clés legacy (person seul / client par personne)."""
    return max(60, min(_DEFAULT_TTL, 3600))


def get_user_identity_ttl_seconds() -> int:
    """TTL bundle ``auth:user:{id}`` — borné 5–15 minutes."""
    raw = _USER_BUNDLE_TTL
    return max(300, min(raw, 900))


def get_user_identity_cached(
    admin_user_id: int,
) -> Union[CachedUserIdentity, UserIdentityCacheMiss]:
    """Lecture bundle ; ne bump pas les métriques (la couche résolution le fait)."""
    if is_redis_cache_enabled():
        r = get_redis_client()
        if r is not None:
            try:
                rk = _key_user_bundle(admin_user_id)
                raw = r.get(rk)
                if raw:
                    bump_redis_hit()
                    logger.info(
                        "redis_cache_hit",
                        extra={"event": "redis_cache_hit", "layer": "identity", "key": rk[:80]},
                    )
                    return _identity_from_json(raw)
                bump_redis_miss()
                logger.info(
                    "redis_cache_miss",
                    extra={"event": "redis_cache_miss", "layer": "identity", "key": rk[:80]},
                )
            except Exception as exc:  # noqa: BLE001
                bump_redis_error()
                logger.warning("redis_cache_error layer=identity op=get err=%s", exc)
    k = _key_user_bundle(admin_user_id)
    with _lock:
        _purge_expired()
        ent = _store.get(k)
        if ent is None:
            return USER_IDENTITY_CACHE_MISS
        val, exp = ent
        if exp <= _now():
            _store.pop(k, None)
            return USER_IDENTITY_CACHE_MISS
        return val


def set_user_identity_cache(admin_user_id: int, identity: CachedUserIdentity) -> None:
    """Écrit le bundle et aligne les entrées legacy avec la même expiration."""
    exp = _now() + get_user_identity_ttl_seconds()
    ttl_sec = get_user_identity_ttl_seconds()
    if is_redis_cache_enabled():
        r = get_redis_client()
        if r is not None:
            try:
                rk = _key_user_bundle(admin_user_id)
                r.setex(rk, ttl_sec, _identity_to_json(identity))
                if identity.person_id is not None:
                    pc = f"auth:person_client:{identity.person_id}"
                    if identity.client_id is not None:
                        r.setex(pc, ttl_sec, str(identity.client_id))
                    else:
                        r.setex(pc, ttl_sec, "null")
            except Exception as exc:  # noqa: BLE001
                bump_redis_error()
                logger.warning("redis_cache_error layer=identity op=setex err=%s", exc)
    with _lock:
        _purge_expired()
        _store[_key_user_bundle(admin_user_id)] = (identity, exp)
        _store[_key_person_by_user(admin_user_id)] = (identity.person_id, exp)
        if identity.person_id is not None and identity.client_id is not None:
            _store[_key_client_by_person(identity.person_id)] = (identity.client_id, exp)


def get_person_id_cached(admin_user_id: int) -> Union[UUID, None, PersonIdCacheMiss]:
    """TTL hit : ``UUID`` ou ``None`` ; sinon ``PERSON_ID_CACHE_MISS``."""
    bundle = get_user_identity_cached(admin_user_id)
    if bundle is not USER_IDENTITY_CACHE_MISS:
        from services.auth.auth_performance_metrics import bump_auth_cache_hit

        bump_auth_cache_hit()
        return bundle.person_id
    k = _key_person_by_user(admin_user_id)
    with _lock:
        _purge_expired()
        ent = _store.get(k)
        if ent is None:
            return PERSON_ID_CACHE_MISS
        val, exp = ent
        if exp <= _now():
            _store.pop(k, None)
            return PERSON_ID_CACHE_MISS
        from services.auth.auth_performance_metrics import bump_auth_cache_hit

        bump_auth_cache_hit()
        return val


def set_person_id_cache(admin_user_id: int, person_id: Optional[UUID]) -> None:
    """Préférer :meth:`set_user_identity_cache` ; conservé pour appels isolés."""
    with _lock:
        _purge_expired()
        k = _key_person_by_user(admin_user_id)
        _store[k] = (person_id, _now() + get_ttl_seconds())


def get_client_id_for_person_cached(db: Session, person_id: UUID) -> Optional[UUID]:
    """``Client.id`` pour ``person_id``, avec cache TTL."""
    if is_redis_cache_enabled():
        r = get_redis_client()
        if r is not None:
            try:
                pc = f"auth:person_client:{person_id}"
                raw = r.get(pc)
                if raw is not None:
                    bump_redis_hit()
                    logger.info(
                        "redis_cache_hit",
                        extra={"event": "redis_cache_hit", "layer": "identity_person_client", "key": pc[:80]},
                    )
                    if raw in ("", "null"):
                        return None
                    return UUID(raw)
                bump_redis_miss()
                logger.info(
                    "redis_cache_miss",
                    extra={"event": "redis_cache_miss", "layer": "identity_person_client", "key": pc[:80]},
                )
            except Exception as exc:  # noqa: BLE001
                bump_redis_error()
                logger.warning("redis_cache_error layer=identity_person_client op=get err=%s", exc)
    k = _key_client_by_person(person_id)
    with _lock:
        _purge_expired()
        ent = _store.get(k)
        if ent is not None:
            val, exp = ent
            if exp > _now():
                from services.auth.auth_performance_metrics import bump_auth_cache_hit

                bump_auth_cache_hit()
                return val
            _store.pop(k, None)

    from services.portfolio_engine.clients.models import Client

    row = db.query(Client).filter(Client.person_id == person_id).first()
    cid: Optional[UUID] = row.id if row is not None else None
    if is_redis_cache_enabled():
        r = get_redis_client()
        if r is not None:
            try:
                pc = f"auth:person_client:{person_id}"
                r.setex(pc, get_ttl_seconds(), str(cid) if cid is not None else "null")
            except Exception as exc:  # noqa: BLE001
                bump_redis_error()
                logger.warning("redis_cache_error layer=identity_person_client op=setex err=%s", exc)
    with _lock:
        _store[k] = (cid, _now() + get_ttl_seconds())
    return cid


def warm_identity_caches_from_user_db(db: Session, user: AdminUser) -> None:
    """Après lecture DB : remplit le bundle ``auth:user:`` (+ legacy)."""
    pid = user.person_id
    cid: Optional[UUID] = None
    if pid is not None:
        cid = get_client_id_for_person_cached(db, pid)
    ident = CachedUserIdentity(
        person_id=pid,
        client_id=cid,
        email=user.email,
        zero_trust_role=getattr(user, "zero_trust_role", None) or "admin",
    )
    set_user_identity_cache(user.id, ident)


def clear_identity_cache_for_tests() -> None:
    with _lock:
        _store.clear()
    try:
        from services.auth.auth_redis import reset_auth_redis_pool_for_tests
        from services.auth.redis_metrics import reset_redis_metrics_for_tests

        reset_auth_redis_pool_for_tests()
        reset_redis_metrics_for_tests()
    except Exception:
        pass
