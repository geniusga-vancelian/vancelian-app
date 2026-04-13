"""Signaux légers (mémoire, best-effort multi-workers) pour logs « suspects »."""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

logger = logging.getLogger("arquantix.auth.security")

_LOCK = Lock()
_REFRESH_REJECTS: Dict[str, Deque[float]] = defaultdict(deque)
_WINDOW_SEC = 60.0
_REJECT_THRESHOLD = 8


def note_refresh_reject(ip_key: str) -> None:
    if not ip_key or ip_key == "unknown":
        return
    now = time.monotonic()
    with _LOCK:
        d = _REFRESH_REJECTS[ip_key]
        while d and now - d[0] > _WINDOW_SEC:
            d.popleft()
        d.append(now)
        if len(d) >= _REJECT_THRESHOLD:
            logger.info(
                "auth.refresh.suspect_ip %s",
                {"reason": "many_refresh_rejects", "ip": _mask_ip(ip_key), "count": len(d)},
            )
            from services.auth.security_events_service import persist_auth_security_event

            persist_auth_security_event(
                user_id=None,
                device_id="",
                event_type="auth.refresh.suspect_ip",
                ip_address=ip_key[:45],
                user_agent=None,
                metadata={"reason": "many_refresh_rejects", "count_reset": True},
                db=None,
            )
            d.clear()


def _mask_ip(ip: str) -> str:
    if len(ip) <= 8:
        return "***"
    return f"{ip[:4]}***{ip[-2:]}"


def reset_signals_for_tests() -> None:
    with _LOCK:
        _REFRESH_REJECTS.clear()
