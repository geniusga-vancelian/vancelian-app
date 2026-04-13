"""
Temporary in-memory TTL store for strategy chat sessions.
Designed to be swappable with Redis later.
"""
from typing import Dict, Any, Optional, Protocol
import time
import threading


class SessionStore(Protocol):
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        ...

    def set(self, session_id: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        ...

    def update(self, session_id: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        ...


class InMemoryTTLStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._store: Dict[str, Dict[str, Any]] = {}

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._store.items() if v.get("expires_at", 0) <= now]
        for key in expired_keys:
            self._store.pop(key, None)

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._cleanup_expired()
            entry = self._store.get(session_id)
            if not entry:
                return None
            return entry.get("data")

    def set(self, session_id: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        with self._lock:
            self._cleanup_expired()
            self._store[session_id] = {
                "data": data,
                "expires_at": time.time() + ttl_seconds,
            }

    def update(self, session_id: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        with self._lock:
            self._cleanup_expired()
            existing = self._store.get(session_id, {}).get("data", {})
            merged = {**existing, **data}
            self._store[session_id] = {
                "data": merged,
                "expires_at": time.time() + ttl_seconds,
            }


# Default store instance
STORE = InMemoryTTLStore()
