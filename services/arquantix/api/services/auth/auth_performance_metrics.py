"""Métriques process-local pour PR C / C.1 — auth DB, cache, JWT-only, mode de résolution, SQL optionnel."""
from __future__ import annotations

import threading
from typing import Literal

ResolutionMode = Literal["jwt_only", "cache", "db"]

_lock = threading.Lock()
_auth_db_hits = 0
_auth_cache_hits = 0
_auth_jwt_only_hits = 0
_auth_resolution_mode_jwt_only = 0
_auth_resolution_mode_cache = 0
_auth_resolution_mode_db = 0
_db_cursor_execute_count = 0


def reset_auth_performance_metrics() -> None:
    """Tests uniquement."""
    global _auth_db_hits, _auth_cache_hits, _auth_jwt_only_hits
    global _auth_resolution_mode_jwt_only, _auth_resolution_mode_cache, _auth_resolution_mode_db
    global _db_cursor_execute_count
    with _lock:
        _auth_db_hits = 0
        _auth_cache_hits = 0
        _auth_jwt_only_hits = 0
        _auth_resolution_mode_jwt_only = 0
        _auth_resolution_mode_cache = 0
        _auth_resolution_mode_db = 0
        _db_cursor_execute_count = 0


def bump_auth_db_hit() -> None:
    global _auth_db_hits
    with _lock:
        _auth_db_hits += 1


def bump_auth_cache_hit() -> None:
    global _auth_cache_hits
    with _lock:
        _auth_cache_hits += 1


def bump_auth_jwt_only_hit() -> None:
    global _auth_jwt_only_hits
    with _lock:
        _auth_jwt_only_hits += 1


def bump_auth_resolution_mode(mode: ResolutionMode) -> None:
    """Compteur par chemin de résolution final (PR C.1) : jwt_only | cache | db."""
    global _auth_resolution_mode_jwt_only, _auth_resolution_mode_cache, _auth_resolution_mode_db
    with _lock:
        if mode == "jwt_only":
            _auth_resolution_mode_jwt_only += 1
        elif mode == "cache":
            _auth_resolution_mode_cache += 1
        else:
            _auth_resolution_mode_db += 1


def bump_db_cursor_execute() -> None:
    global _db_cursor_execute_count
    with _lock:
        _db_cursor_execute_count += 1


def get_auth_performance_metrics() -> dict[str, int]:
    with _lock:
        return {
            "auth_db_hits_count": _auth_db_hits,
            "auth_cache_hits_count": _auth_cache_hits,
            "auth_jwt_only_count": _auth_jwt_only_hits,
            "auth_resolution_mode_jwt_only": _auth_resolution_mode_jwt_only,
            "auth_resolution_mode_cache": _auth_resolution_mode_cache,
            "auth_resolution_mode_db": _auth_resolution_mode_db,
            "db_cursor_execute_count": _db_cursor_execute_count,
        }


def get_auth_resolution_mode_counts() -> dict[str, int]:
    with _lock:
        return {
            "jwt_only": _auth_resolution_mode_jwt_only,
            "cache": _auth_resolution_mode_cache,
            "db": _auth_resolution_mode_db,
        }
