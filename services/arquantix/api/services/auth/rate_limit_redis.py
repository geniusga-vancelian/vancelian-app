"""PR G — rate limit distribué des échecs signature device (fenêtre 60s, INCR + EXPIRE)."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from services.auth.redis_client import get_redis_client
from services.auth.redis_metrics import bump_redis_error
from services.security.security_env import is_redis_cache_enabled, is_signature_failure_rl_redis_enabled

logger = logging.getLogger("arquantix.auth.rate_limit_redis")

_RL_WINDOW_SEC = 60


def _rl_key(user_id: int, device_id: str) -> str:
    safe = device_id.replace(":", "_")[:200]
    return f"rl:device_sig_fail:{user_id}:{safe}"


def parse_device_key(device_key: str) -> Tuple[Optional[int], str]:
    """``device_key`` = ``f"{user_id}:{device_id}"`` (PR F / D3)."""
    if ":" not in device_key:
        return None, device_key
    uid_s, _, rest = device_key.partition(":")
    try:
        return int(uid_s), rest
    except ValueError:
        return None, device_key


def redis_increment_signature_failure(user_id: int, device_id: str) -> Optional[int]:
    """
    Incrémente le compteur Redis et retourne la nouvelle valeur, ou ``None`` si indisponible.
    """
    if not is_redis_cache_enabled() or not is_signature_failure_rl_redis_enabled():
        return None
    r = get_redis_client()
    if r is None:
        return None
    key = _rl_key(user_id, device_id)
    try:
        n = int(r.incr(key))
        if n == 1:
            r.expire(key, _RL_WINDOW_SEC)
        return n
    except Exception as exc:  # noqa: BLE001
        bump_redis_error()
        logger.warning("redis_rl_incr_error: %s", exc)
        return None


def redis_get_signature_failure_count(user_id: int, device_id: str) -> Optional[int]:
    """Lecture seule du compteur Redis (sans incrément)."""
    if not is_redis_cache_enabled() or not is_signature_failure_rl_redis_enabled():
        return None
    r = get_redis_client()
    if r is None:
        return None
    key = _rl_key(user_id, device_id)
    try:
        v = r.get(key)
        return int(v) if v is not None else 0
    except Exception as exc:  # noqa: BLE001
        bump_redis_error()
        logger.warning("redis_rl_get_error: %s", exc)
        return None
