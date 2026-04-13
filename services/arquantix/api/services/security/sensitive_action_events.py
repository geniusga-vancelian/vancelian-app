"""Événements SIEM pour actions sensibles (complète les hooks ``auth.session.*`` existants)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event


def _meta(
    *,
    action_key: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    m: Dict[str, Any] = {"action_key": (action_key or "").strip().lower()}
    if extra:
        m.update(extra)
    return m


def record_sensitive_action_completed(
    *,
    user_id: int,
    action_key: str,
    request: Optional[Request],
    db: Session,
    device_id: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not is_security_events_enabled():
        return
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    if ua and len(ua) > 512:
        ua = ua[:512]
    persist_auth_security_event(
        user_id=user_id,
        device_id=device_id[:128],
        event_type="sensitive_action.completed",
        ip_address=ip,
        user_agent=ua,
        metadata=_meta(action_key=action_key, extra=extra),
        db=db,
    )


def record_sensitive_action_failed(
    *,
    user_id: int,
    action_key: str,
    request: Optional[Request],
    db: Session,
    reason: str,
    device_id: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not is_security_events_enabled():
        return
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    if ua and len(ua) > 512:
        ua = ua[:512]
    m = _meta(action_key=action_key, extra=extra)
    m["failure_reason"] = reason[:256]
    persist_auth_security_event(
        user_id=user_id,
        device_id=device_id[:128],
        event_type="sensitive_action.failed",
        ip_address=ip,
        user_agent=ua,
        metadata=m,
        db=db,
    )
