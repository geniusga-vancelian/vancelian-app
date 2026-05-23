"""Garde-fous pour les routes HTTP **dev/test** Privy (jamais en production)."""
from __future__ import annotations

import logging
import os

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


def privy_dev_tools_allowed(request: Request) -> bool:
    """
    True uniquement hors production ou sous tests pytest (``app.state.testing``).

    - ``ENV=production`` → toujours False.
    - ``app.state.testing`` (pytest) → True pour permettre les tests d’intégration.
    - Sinon : ``ENV`` ∈ {test, testing, local, dev, development} ou :func:`core.env.is_dev_mode`.
    """
    env = (os.getenv("ENV") or "").strip().lower()
    if env == "production":
        return False
    if getattr(request.app.state, "testing", False):
        return True
    if env in ("test", "testing", "local", "dev", "development"):
        return True
    from core.env import is_dev_mode

    return is_dev_mode()


def ensure_privy_dev_tools_or_403(request: Request) -> None:
    if privy_dev_tools_allowed(request):
        return
    logger.warning(
        "privy_dev_link_forbidden",
        extra={"event": "privy_dev_link_forbidden", "path": request.url.path},
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "privy.dev_link_forbidden",
            "message": "Outils Privy dev désactivés (production ou environnement non dev).",
        },
    )
