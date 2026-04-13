"""Connexion Redis dédiée au module auth (rate limiting).

Priorité : ``AUTH_REDIS_URL``, puis ``REDIS_URL`` (compat dev).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)

_pool: Optional[redis.ConnectionPool] = None


def _redis_socket_timeout_sec() -> float:
    try:
        return max(0.02, min(2.0, float(os.getenv("REDIS_SOCKET_TIMEOUT_SEC", "0.1"))))
    except ValueError:
        return 0.1


def auth_redis_url() -> str:
    return (
        os.getenv("AUTH_REDIS_URL", "").strip()
        or os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
    )


def get_auth_redis() -> Optional[redis.Redis]:
    """Client Redis pour l’auth ; None si indisponible.

    Le pool est validé par un ping **à la création uniquement** (pas à chaque appel)
    pour limiter la latence en charge (PR G).
    """
    global _pool
    url = auth_redis_url()
    if not url:
        return None
    to = _redis_socket_timeout_sec()
    if _pool is None:
        try:
            trial = redis.ConnectionPool.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=to,
                socket_timeout=to,
            )
            client = redis.Redis(connection_pool=trial)
            client.ping()
            _pool = trial
        except Exception as exc:
            logger.warning("auth redis pool failed: %s", exc)
            return None
    try:
        return redis.Redis(connection_pool=_pool)
    except Exception as exc:
        logger.warning("auth redis client failed: %s", exc)
        return None


def ping_auth_redis() -> bool:
    r = get_auth_redis()
    return r is not None


def reset_auth_redis_pool_for_tests() -> None:
    global _pool
    _pool = None
