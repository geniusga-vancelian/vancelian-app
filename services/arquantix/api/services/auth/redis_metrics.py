"""PR G — compteurs process-local Redis (hits / miss / erreurs)."""
from __future__ import annotations

import threading

_lock = threading.Lock()
_redis_hit = 0
_redis_miss = 0
_redis_error = 0


def reset_redis_metrics_for_tests() -> None:
    global _redis_hit, _redis_miss, _redis_error
    with _lock:
        _redis_hit = 0
        _redis_miss = 0
        _redis_error = 0


def bump_redis_hit() -> None:
    global _redis_hit
    with _lock:
        _redis_hit += 1


def bump_redis_miss() -> None:
    global _redis_miss
    with _lock:
        _redis_miss += 1


def bump_redis_error() -> None:
    global _redis_error
    with _lock:
        _redis_error += 1


def get_redis_metrics() -> dict[str, int]:
    with _lock:
        return {
            "redis_hit": _redis_hit,
            "redis_miss": _redis_miss,
            "redis_error": _redis_error,
        }
