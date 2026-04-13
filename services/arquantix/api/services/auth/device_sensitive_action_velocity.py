""" Fenêtre glissante : fréquence des actions sensibles signées (signal risque PR D4.1). """
from __future__ import annotations

import threading
import time
from typing import Dict, Tuple

_lock = threading.Lock()
_window: Dict[str, Tuple[float, int]] = {}
_WINDOW_SEC = 300.0


def reset_sensitive_action_velocity_for_tests() -> None:
    global _window
    with _lock:
        _window.clear()


def record_sensitive_action(user_id: int, device_id: str) -> None:
    """Incrémente le compteur après une action sensible réussie."""
    key = f"{user_id}:{device_id}"
    now = time.monotonic()
    with _lock:
        dead = [k for k, (t0, _) in _window.items() if now - t0 > _WINDOW_SEC]
        for k in dead:
            _window.pop(k, None)
        t0, n = _window.get(key, (now, 0))
        if now - t0 > _WINDOW_SEC:
            t0, n = now, 0
        n += 1
        _window[key] = (t0, n)


def get_sensitive_action_count(user_id: int, device_id: str) -> int:
    """Nombre d’actions sensibles réussies dans la fenêtre (sans incrémenter)."""
    key = f"{user_id}:{device_id}"
    now = time.monotonic()
    with _lock:
        dead = [k for k, (t0, _) in _window.items() if now - t0 > _WINDOW_SEC]
        for k in dead:
            _window.pop(k, None)
        t0, n = _window.get(key, (now, 0))
        if now - t0 > _WINDOW_SEC:
            return 0
        return n
