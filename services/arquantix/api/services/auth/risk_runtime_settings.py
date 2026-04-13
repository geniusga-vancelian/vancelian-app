"""PR F.5 — overrides runtime (dry-run) via Redis, sans redéploiement."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from services.auth.redis_client import get_redis_client
from services.security.security_env import _env_truthy, is_redis_cache_enabled

logger = logging.getLogger("arquantix.auth.risk_runtime")

REDIS_KEY_DRY_RUN = "arquantix:risk:device_rules_dry_run"


def redis_dry_run_override_available() -> bool:
    return is_redis_cache_enabled() and get_redis_client() is not None


def _read_redis_override() -> Optional[bool]:
    if not is_redis_cache_enabled():
        return None
    r = get_redis_client()
    if r is None:
        return None
    try:
        v = r.get(REDIS_KEY_DRY_RUN)
        if v is None:
            return None
        s = str(v).strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("risk_runtime_redis_read_failed: %s", exc)
    return None


def get_dry_run_effective() -> Tuple[bool, str]:
    o = _read_redis_override()
    if o is not None:
        return o, "redis"
    return _env_truthy("DEVICE_RISK_RULES_DRY_RUN", default="false"), "env"


def set_dry_run_override(enabled: bool) -> None:
    if not is_redis_cache_enabled():
        raise RuntimeError("REDIS_ENABLED requis pour override runtime dry-run")
    r = get_redis_client()
    if r is None:
        raise RuntimeError("Redis indisponible")
    try:
        r.set(REDIS_KEY_DRY_RUN, "1" if enabled else "0", ex=86400 * 365)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Redis set failed: {exc}") from exc
