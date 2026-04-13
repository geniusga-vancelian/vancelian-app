"""Rate limiting pour /auth/login (par IP), /auth/refresh et /auth/revoke (par device).

AUTH_RL_BACKEND=memory|redis|auto (défaut auto)
Quotas lus depuis l’env à chaque requête (tests via monkeypatch).
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def _auth_rl_exceeded(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": {
                "code": "rate_limited",
                "message": "Too many authentication requests. Please wait and try again.",
                "retry_after": retry_after,
            }
        },
    )


def _load_login_limits() -> Tuple[int, float]:
    m = max(1, int(os.getenv("AUTH_RL_LOGIN_MAX", "5")))
    w = max(1.0, float(os.getenv("AUTH_RL_LOGIN_WINDOW_SEC", "60")))
    return m, w


def _load_refresh_limits() -> Tuple[int, float]:
    m = max(1, int(os.getenv("AUTH_RL_REFRESH_MAX", "20")))
    w = max(1.0, float(os.getenv("AUTH_RL_REFRESH_WINDOW_SEC", "60")))
    return m, w


def _load_revoke_limits() -> Tuple[int, float]:
    m = max(1, int(os.getenv("AUTH_RL_REVOKE_MAX", "10")))
    w = max(1.0, float(os.getenv("AUTH_RL_REVOKE_WINDOW_SEC", "60")))
    return m, w


class AuthRateLimiter(ABC):
    @abstractmethod
    def check_login(self, ip_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def check_refresh(self, device_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def check_revoke(self, device_key: str) -> None:
        raise NotImplementedError


class MemoryAuthRateLimiter(AuthRateLimiter):
    def __init__(self) -> None:
        self._lock = Lock()
        self._login: Dict[str, List[float]] = defaultdict(list)
        self._refresh: Dict[str, List[float]] = defaultdict(list)
        self._revoke: Dict[str, List[float]] = defaultdict(list)

    def _hit(self, buckets: Dict[str, List[float]], key: str, max_n: int, window: float) -> None:
        now = time.monotonic()
        with self._lock:
            b = buckets[key]
            b[:] = [t for t in b if now - t < window]
            if len(b) >= max_n:
                raise _auth_rl_exceeded(int(window) + 1)
            b.append(now)

    def check_login(self, ip_key: str) -> None:
        mx, w = _load_login_limits()
        self._hit(self._login, ip_key, mx, w)

    def check_refresh(self, device_key: str) -> None:
        mx, w = _load_refresh_limits()
        self._hit(self._refresh, device_key, mx, w)

    def check_revoke(self, device_key: str) -> None:
        mx, w = _load_revoke_limits()
        self._hit(self._revoke, device_key, mx, w)


def _sanitize_rl_key(s: str) -> str:
    out = "".join(c if c.isalnum() or c in "._-" else "_" for c in s)
    return out[:200] if out else "empty"


class RedisIncrAuthRateLimiter(AuthRateLimiter):
    """Fenêtre fixe distribuée : INCR + EXPIRE (compatible multi-process)."""

    def __init__(self, redis_client, key_prefix: str = "arq:auth:rl:ic") -> None:
        self._r = redis_client
        self._pfx = key_prefix

    def _check(self, kind: str, client_key: str, max_n: int, window_sec: int) -> None:
        key = f"{self._pfx}:{kind}:{_sanitize_rl_key(client_key)}"
        n = int(self._r.incr(key))
        if n == 1:
            self._r.expire(key, window_sec)
        else:
            ttl = self._r.ttl(key)
            if ttl == -1:
                self._r.expire(key, window_sec)
        if n > max_n:
            raise _auth_rl_exceeded(window_sec)

    def check_login(self, ip_key: str) -> None:
        mx, w = _load_login_limits()
        self._check("login", ip_key, mx, int(w))

    def check_refresh(self, device_key: str) -> None:
        mx, w = _load_refresh_limits()
        self._check("refresh", device_key, mx, int(w))

    def check_revoke(self, device_key: str) -> None:
        mx, w = _load_revoke_limits()
        self._check("revoke", device_key, mx, int(w))


_limiter_singleton: Optional[AuthRateLimiter] = None


def build_auth_rate_limiter() -> AuthRateLimiter:
    global _limiter_singleton
    if _limiter_singleton is not None:
        return _limiter_singleton

    from services.auth.auth_bootstrap import is_production_environment
    from services.auth.auth_redis import get_auth_redis

    backend = (os.getenv("AUTH_RL_BACKEND") or "auto").strip().lower()
    prod = is_production_environment()

    if prod:
        r = get_auth_redis()
        if r is None:
            raise RuntimeError(
                "AUTH_RL_BACKEND must be redis in production and AUTH_REDIS_URL must be reachable."
            )
        _limiter_singleton = RedisIncrAuthRateLimiter(r)
        logger.info("auth_rate_limiter backend=redis (production)")
        return _limiter_singleton

    if backend == "memory":
        _limiter_singleton = MemoryAuthRateLimiter()
        logger.info("auth_rate_limiter backend=memory")
        return _limiter_singleton

    if backend == "redis":
        r = get_auth_redis()
        if r is None:
            logger.warning("AUTH_RL_BACKEND=redis but Redis unavailable — memory fallback (dev)")
            _limiter_singleton = MemoryAuthRateLimiter()
        else:
            _limiter_singleton = RedisIncrAuthRateLimiter(r)
            logger.info("auth_rate_limiter backend=redis")
        return _limiter_singleton

    r = get_auth_redis()
    if r is not None:
        _limiter_singleton = RedisIncrAuthRateLimiter(r)
        logger.info("auth_rate_limiter backend=redis(auto)")
    else:
        _limiter_singleton = MemoryAuthRateLimiter()
        logger.info("auth_rate_limiter backend=memory(auto)")
    return _limiter_singleton


def reset_auth_rate_limiter_for_tests() -> None:
    global _limiter_singleton
    _limiter_singleton = None


def client_ip_for_rl(request) -> str:
    if os.getenv("AUTH_TRUST_X_FORWARDED_FOR", "").strip() in ("1", "true", "yes"):
        xff = request.headers.get("x-forwarded-for") or ""
        first = xff.split(",")[0].strip()
        if first:
            return first[:45]
    if request.client and request.client.host:
        return request.client.host[:45]
    return "unknown"
