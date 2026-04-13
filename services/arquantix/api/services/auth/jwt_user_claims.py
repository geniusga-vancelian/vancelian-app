"""
Claims JWT pour sessions **utilisateur** (access + refresh).

Invariant (PR5) — à ne jamais relâcher :

    JWT ``sub`` MUST always be ``au:<admin_users.id>`` (entier > 0).
    Any other format is invalid and rejected (voir ``jwt_subject_resolution``).

- ``sub_typ`` : ``user_id``.
- ``person_id`` : liaison Person si présent (la lecture accepte encore ``pid`` sur d’anciens jetons).

Les jetons spéciaux (ex. ``registration:2fa``) sont construits ailleurs.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from database import AdminUser

logger = logging.getLogger(__name__)

USER_JWT_SUB_PREFIX = "au:"

# Compteurs process-local — complément aux logs DEBUG ; agrégation Prometheus/APM recommandée en prod.
_emit_lock = threading.Lock()
_jwt_user_tokens_emitted_count = 0


def format_user_jwt_sub(user_id: int) -> str:
    """Format canonique d’émission du sujet utilisateur (access + refresh)."""
    return f"{USER_JWT_SUB_PREFIX}{int(user_id)}"


def get_jwt_emission_metrics() -> dict[str, int]:
    """Nombre de paires access/refresh utilisateur émises depuis le démarrage du processus."""
    with _emit_lock:
        return {"jwt_user_tokens_emitted_count": _jwt_user_tokens_emitted_count}


def reset_jwt_emission_metrics() -> None:
    """Tests uniquement."""
    global _jwt_user_tokens_emitted_count
    with _emit_lock:
        _jwt_user_tokens_emitted_count = 0


def _bump_emission_metric() -> None:
    global _jwt_user_tokens_emitted_count
    with _emit_lock:
        _jwt_user_tokens_emitted_count += 1


def build_user_jwt_access_base_claims(user: AdminUser) -> Dict[str, Any]:
    """
    Claims de base pour l’access (refresh aligné sur le même ``sub``).

    - ``sub`` : ``au:<id>`` via :func:`format_user_jwt_sub`
    - ``sub_typ`` : ``user_id``
    - ``person_id`` : UUID Person si présent (pas de duplication ``pid`` à l’émission)
    """
    claims: Dict[str, Any] = {
        "sub": format_user_jwt_sub(user.id),
        "sub_typ": "user_id",
    }
    if user.person_id is not None:
        claims["person_id"] = str(user.person_id)
    return claims


def log_jwt_subject_emitted(
    *,
    user: AdminUser,
    context: str,
    route: Optional[str] = None,
) -> None:
    """
    DEBUG : détail par émission (éviter le bruit INFO en prod).

    Un compteur agrégé : :func:`get_jwt_emission_metrics` (``jwt_user_tokens_emitted_count``).
    """
    sub_val = format_user_jwt_sub(user.id)
    _bump_emission_metric()
    logger.debug(
        "jwt_subject_emitted",
        extra={
            "event": "jwt_subject_emitted",
            "user_id": user.id,
            "sub": sub_val,
            "sub_typ": "user_id",
            "has_person_id": user.person_id is not None,
            "context": context,
            "route": route or "",
        },
    )
