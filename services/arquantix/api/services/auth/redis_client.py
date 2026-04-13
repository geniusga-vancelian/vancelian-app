"""PR G — accès Redis pour caches distribués (réutilise le pool ``auth_redis``)."""
from __future__ import annotations

import logging
from typing import Optional

import redis

from services.auth.auth_redis import get_auth_redis
from services.security.security_env import is_redis_cache_enabled

logger = logging.getLogger("arquantix.auth.redis_client")


def get_redis_client() -> Optional[redis.Redis]:
    """
    Client Redis partagé, ou ``None`` si désactivé / indisponible.

    Respecte ``REDIS_ENABLED=false`` : aucune connexion (fallback local uniquement).
    """
    if not is_redis_cache_enabled():
        return None
    client = get_auth_redis()
    if client is None:
        from services.security.security_env import is_redis_fallback_local_enabled

        if is_redis_fallback_local_enabled():
            logger.debug("redis_cache_redis_unavailable_fallback_local")
    return client


def redis_available() -> bool:
    """``True`` si un appel Redis peut être obtenu (ping initial OK côté pool auth)."""
    return get_redis_client() is not None
