"""Middleware optionnel : touche légère ``last_activity_at`` sur sessions authentifiées (JWT ``sid``)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Callable

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from auth import ALGORITHM, SECRET_KEY
from database import SessionLocal
from services.security.session_intelligence_service import (
    is_session_intelligence_enabled,
    touch_last_activity_from_token,
)

logger = logging.getLogger("arquantix.security.session_intelligence")

_SKIP_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/revoke",
)


def _skip_path(path: str) -> bool:
    p = (path or "").lower()
    return any(p.startswith(pref) for pref in _SKIP_PREFIXES)


def _sync_touch_activity(request: Request) -> None:
    if not is_session_intelligence_enabled():
        return
    if _skip_path(request.url.path):
        return
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return
    token = auth[7:].strip()
    if not token:
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return
    sid = payload.get("sid")
    if not sid:
        return
    try:
        su = uuid.UUID(str(sid))
    except (ValueError, TypeError):
        return
    db = SessionLocal()
    try:
        touch_last_activity_from_token(db, session_uuid=su, request=request)
    except Exception as exc:  # noqa: BLE001
        logger.debug("session intel touch skipped: %s", exc)
    finally:
        db.close()


class SessionIntelligenceActivityMiddleware(BaseHTTPMiddleware):
    """Après la requête : met à jour l’activité si JWT valide avec ``sid`` (session courte dédiée)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if response.status_code >= 500:
            return response
        try:
            await asyncio.to_thread(_sync_touch_activity, request)
        except Exception as exc:  # noqa: BLE001
            logger.debug("session intel middleware: %s", exc)
        return response
