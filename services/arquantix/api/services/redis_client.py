"""Redis connection singleton.

Uses a connection pool so all callers share the same TCP connections.
Falls back gracefully when Redis is unavailable (returns None).
"""
import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)

_pool: Optional[redis.ConnectionPool] = None


def get_redis() -> Optional[redis.Redis]:
    """Return a Redis client backed by a shared connection pool.

    Returns None if REDIS_URL is not set or connection fails on first use.
    """
    global _pool
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if _pool is None:
        try:
            _pool = redis.ConnectionPool.from_url(url, decode_responses=True)
        except Exception:
            logger.warning("Redis connection pool creation failed (url=%s)", url)
            return None
    try:
        client = redis.Redis(connection_pool=_pool)
        client.ping()
        return client
    except Exception:
        logger.warning("Redis unreachable (url=%s)", url)
        return None
