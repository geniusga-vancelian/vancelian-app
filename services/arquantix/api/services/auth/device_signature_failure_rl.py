"""PR D3 — rate limit des échecs de vérification signature (par device).

PR G : fenêtre distribuée Redis (``rl:device_sig_fail:…``) si ``REDIS_ENABLED`` ;
sinon fenêtre mémoire process (historique).
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Tuple

from services.auth.device_pr_d3_policy import device_signature_failure_rate_limit_max
from services.auth.rate_limit_redis import (
    parse_device_key,
    redis_get_signature_failure_count,
    redis_increment_signature_failure,
)
from services.security.security_env import is_redis_cache_enabled, is_signature_failure_rl_redis_enabled

_lock = threading.Lock()
_window: Dict[str, Tuple[float, int]] = {}


def reset_device_signature_failure_rl_for_tests() -> None:
    global _window
    with _lock:
        _window.clear()


def _local_get_signature_failure_count(device_key: str) -> int:
    now = time.monotonic()
    window_sec = 60.0
    with _lock:
        dead = [k for k, (t0, _) in _window.items() if now - t0 > window_sec]
        for k in dead:
            _window.pop(k, None)
        t0, n = _window.get(device_key, (now, 0))
        if now - t0 > window_sec:
            return 0
        return n


def get_signature_failure_count(device_key: str) -> int:
    """Nombre d’échecs récents (fenêtre 60s) sans incrémenter — pour le score de risque PR D4."""
    if is_redis_cache_enabled() and is_signature_failure_rl_redis_enabled():
        uid, did = parse_device_key(device_key)
        if uid is not None:
            rc = redis_get_signature_failure_count(uid, did)
            if rc is not None:
                return rc
    return _local_get_signature_failure_count(device_key)


def _local_check_and_record(device_key: str, max_hits: int) -> None:
    from fastapi import HTTPException, status

    now = time.monotonic()
    window_sec = 60.0
    with _lock:
        dead = [k for k, (t0, _) in _window.items() if now - t0 > window_sec]
        for k in dead:
            _window.pop(k, None)
        t0, n = _window.get(device_key, (now, 0))
        if now - t0 > window_sec:
            t0, n = now, 0
        n += 1
        _window[device_key] = (t0, n)
        if n > max_hits:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "device_signature_rate_limited"},
            )


def check_and_record_signature_failure(device_key: str) -> None:
    """Lève HTTP 429 si trop d'échecs dans la fenêtre glissante (60s)."""
    max_hits = device_signature_failure_rate_limit_max()
    if is_redis_cache_enabled() and is_signature_failure_rl_redis_enabled():
        uid, did = parse_device_key(device_key)
        if uid is not None:
            n = redis_increment_signature_failure(uid, did)
            if n is not None:
                if n > max_hits:
                    from fastapi import HTTPException, status

                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={"code": "device_signature_rate_limited"},
                    )
                return
    _local_check_and_record(device_key, max_hits)
