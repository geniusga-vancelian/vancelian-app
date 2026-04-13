"""Rate limiting for /api/address/* — memory or Redis sliding window.

Switch: set ADDRESS_RL_BACKEND=redis|memory|auto (default auto: Redis if reachable).
Quotas: ADDRESS_RL_AUTOCOMPLETE_MAX (default 60), ADDRESS_RL_DETAILS_MAX (default 30)
        per ADDRESS_RL_WINDOW_SEC (default 60).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def _rate_limit_exceeded(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": {
                "code": "rate_limited",
                "message": "Too many address lookup requests. Please wait and try again.",
                "retry_after": retry_after,
            }
        },
    )


class AddressRateLimiter(ABC):
    """Abstract limiter: separate buckets for autocomplete vs details."""

    @abstractmethod
    def check_autocomplete(self, client_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def check_details(self, client_key: str) -> None:
        raise NotImplementedError


class MemorySlidingWindowLimiter(AddressRateLimiter):
    def __init__(
        self,
        *,
        autocomplete_max: int,
        details_max: int,
        window_sec: float,
    ) -> None:
        self._auto_max = autocomplete_max
        self._det_max = details_max
        self._window = window_sec
        self._lock = Lock()
        self._auto: Dict[str, List[float]] = defaultdict(list)
        self._det: Dict[str, List[float]] = defaultdict(list)

    def _hit(self, buckets: Dict[str, List[float]], key: str, max_per_window: int) -> None:
        now = time.monotonic()
        with self._lock:
            b = buckets[key]
            b[:] = [t for t in b if now - t < self._window]
            if len(b) >= max_per_window:
                raise _rate_limit_exceeded(int(self._window) + 1)
            b.append(now)

    def check_autocomplete(self, client_key: str) -> None:
        self._hit(self._auto, client_key, self._auto_max)

    def check_details(self, client_key: str) -> None:
        self._hit(self._det, client_key, self._det_max)


class RedisSlidingWindowLimiter(AddressRateLimiter):
    """Redis sorted-set sliding window (works across workers)."""

    def __init__(
        self,
        redis_client,
        *,
        autocomplete_max: int,
        details_max: int,
        window_sec: float,
        key_prefix: str = "arq:addr:rl",
    ) -> None:
        self._r = redis_client
        self._auto_max = autocomplete_max
        self._det_max = details_max
        self._window = float(window_sec)
        self._pfx = key_prefix

    def _check(self, kind: str, client_key: str, max_per_window: int) -> None:
        now = time.time()
        key = f"{self._pfx}:{kind}:{client_key}"
        cutoff = now - self._window
        member = f"{now:.6f}:{uuid.uuid4().hex}"
        pipe = self._r.pipeline()
        pipe.zremrangebyscore(key, "-inf", cutoff)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, int(self._window) + 2)
        _, _, count, _ = pipe.execute()
        if count > max_per_window:
            raise _rate_limit_exceeded(int(self._window) + 1)

    def check_autocomplete(self, client_key: str) -> None:
        self._check("autocomplete", client_key, self._auto_max)

    def check_details(self, client_key: str) -> None:
        self._check("details", client_key, self._det_max)


def _load_limits() -> Tuple[int, int, float]:
    ac = int(os.getenv("ADDRESS_RL_AUTOCOMPLETE_MAX", "60"))
    dt = int(os.getenv("ADDRESS_RL_DETAILS_MAX", "30"))
    w = float(os.getenv("ADDRESS_RL_WINDOW_SEC", "60"))
    return max(1, ac), max(1, dt), max(1.0, w)


def build_address_rate_limiter() -> AddressRateLimiter:
    ac_max, dt_max, window = _load_limits()
    backend = (os.getenv("ADDRESS_RL_BACKEND") or "auto").strip().lower()

    if backend == "memory":
        logger.info("address_rate_limiter backend=memory ac=%s dt=%s w=%s", ac_max, dt_max, window)
        return MemorySlidingWindowLimiter(
            autocomplete_max=ac_max,
            details_max=dt_max,
            window_sec=window,
        )

    if backend == "redis":
        from services.redis_client import get_redis

        r = get_redis()
        if r is None:
            logger.warning("ADDRESS_RL_BACKEND=redis but Redis unavailable — falling back to memory")
            return MemorySlidingWindowLimiter(
                autocomplete_max=ac_max,
                details_max=dt_max,
                window_sec=window,
            )
        logger.info("address_rate_limiter backend=redis ac=%s dt=%s w=%s", ac_max, dt_max, window)
        return RedisSlidingWindowLimiter(
            r,
            autocomplete_max=ac_max,
            details_max=dt_max,
            window_sec=window,
        )

    # auto
    from services.redis_client import get_redis

    r = get_redis()
    if r is not None:
        logger.info("address_rate_limiter backend=redis(auto) ac=%s dt=%s w=%s", ac_max, dt_max, window)
        return RedisSlidingWindowLimiter(
            r,
            autocomplete_max=ac_max,
            details_max=dt_max,
            window_sec=window,
        )
    logger.info("address_rate_limiter backend=memory(auto) ac=%s dt=%s w=%s", ac_max, dt_max, window)
    return MemorySlidingWindowLimiter(
        autocomplete_max=ac_max,
        details_max=dt_max,
        window_sec=window,
    )


_limiter_singleton: Optional[AddressRateLimiter] = None


def get_address_rate_limiter() -> AddressRateLimiter:
    global _limiter_singleton
    if _limiter_singleton is None:
        _limiter_singleton = build_address_rate_limiter()
    return _limiter_singleton


def reset_address_rate_limiter_for_tests() -> None:
    global _limiter_singleton
    _limiter_singleton = None
