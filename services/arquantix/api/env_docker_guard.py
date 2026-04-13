"""Détection d’URLs de services incohérentes quand l’API tourne dans un conteneur Docker."""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _in_docker() -> bool:
    return Path("/.dockerenv").is_file()


def validate_docker_runtime_env() -> list[str]:
    """Retourne des messages d’erreur à logger ; liste vide si OK ou hors Docker."""
    if not _in_docker():
        return []
    msgs: list[str] = []
    du = (os.getenv("DATABASE_URL") or "").strip()
    if du and ("localhost" in du or "127.0.0.1" in du):
        msgs.append(
            "DATABASE_URL référence localhost/127.0.0.1 dans un conteneur — "
            "attendu un host de service Compose (ex. arquantix-db:5432)."
        )
    ru = (os.getenv("REDIS_URL") or os.getenv("AUTH_REDIS_URL") or "").strip()
    if ru and ("127.0.0.1" in ru or "localhost" in ru):
        msgs.append(
            "REDIS_URL / AUTH_REDIS_URL référence localhost dans un conteneur — "
            "attendu redis://arquantix-redis:6379/0"
        )
    return msgs


def log_docker_env_validation() -> None:
    for msg in validate_docker_runtime_env():
        logger.error("ENV Docker: %s", msg)
        print(f"[API] ERROR (env Docker): {msg}")
