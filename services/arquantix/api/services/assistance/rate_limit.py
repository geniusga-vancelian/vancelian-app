"""Rate limiter dédié `/assistance/chat/turn` — 30 req/min/client par défaut.

Réutilise la mécanique mémoire/Redis du module `auth_rate_limit` (mêmes
backends, mêmes garde-fous prod) pour éviter la duplication. La clé est le
`client_id` (UUID) ; on n'utilise pas l'IP pour ne pas pénaliser plusieurs
clients derrière le même NAT.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional

from fastapi import HTTPException, status

from services.assistance.config import assistance_rate_limit

logger = logging.getLogger(__name__)


def _exceeded(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": {
                "code": "rate_limited",
                "message": "Too many assistance requests. Please wait and try again.",
                "retry_after": retry_after,
            }
        },
    )


def _sanitize_key(s: str) -> str:
    out = "".join(c if c.isalnum() or c in "._-" else "_" for c in s)
    return out[:200] if out else "empty"


class _MemoryLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._buckets: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str, max_n: int, window: float) -> None:
        now = time.monotonic()
        with self._lock:
            b = self._buckets[key]
            b[:] = [t for t in b if now - t < window]
            if len(b) >= max_n:
                raise _exceeded(int(window) + 1)
            b.append(now)


class _RedisLimiter:
    """Fenêtre fixe distribuée (INCR + EXPIRE)."""

    def __init__(self, redis_client) -> None:
        self._r = redis_client
        self._pfx = "arq:assistance:rl"

    def check(self, key: str, max_n: int, window: float) -> None:
        rkey = f"{self._pfx}:{_sanitize_key(key)}"
        n = int(self._r.incr(rkey))
        if n == 1:
            self._r.expire(rkey, int(window))
        else:
            ttl = self._r.ttl(rkey)
            if ttl == -1:
                self._r.expire(rkey, int(window))
        if n > max_n:
            raise _exceeded(int(window))


_singleton: Optional[object] = None
_singleton_lock = Lock()


def _build_limiter():
    """Sélection backend identique à `auth_rate_limit` : prod=redis obligatoire."""
    from services.auth.auth_bootstrap import is_production_environment
    from services.auth.auth_redis import get_auth_redis

    backend = (os.getenv("ASSISTANCE_RL_BACKEND") or "auto").strip().lower()
    prod = is_production_environment()

    if prod:
        r = get_auth_redis()
        if r is None:
            raise RuntimeError(
                "ASSISTANCE_RL_BACKEND=redis required in production "
                "(AUTH_REDIS_URL must be reachable)."
            )
        logger.info("assistance_rate_limiter backend=redis (production)")
        return _RedisLimiter(r)

    if backend == "memory":
        logger.info("assistance_rate_limiter backend=memory")
        return _MemoryLimiter()

    if backend == "redis":
        r = get_auth_redis()
        if r is None:
            logger.warning(
                "ASSISTANCE_RL_BACKEND=redis but Redis unavailable — memory fallback (dev)"
            )
            return _MemoryLimiter()
        return _RedisLimiter(r)

    r = get_auth_redis()
    if r is not None:
        logger.info("assistance_rate_limiter backend=redis(auto)")
        return _RedisLimiter(r)
    logger.info("assistance_rate_limiter backend=memory(auto)")
    return _MemoryLimiter()


def _get_limiter():
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = _build_limiter()
    return _singleton


def check_assistance_quota(client_id: str) -> None:
    """Garde-fou requête : lève 429 si `client_id` dépasse le quota."""
    max_n, window = assistance_rate_limit()
    _get_limiter().check(f"client:{client_id}", max_n, window)


def reset_for_tests() -> None:
    """Tests : remet à zéro le singleton (recharge env / monkeypatch)."""
    global _singleton
    _singleton = None
