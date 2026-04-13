"""Persistance des décisions critiques (auth_security_decisions) + log applicatif."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from database import AuthSecurityDecision
from services.security.zero_trust.request_security_context import RequestSecurityContext

logger = logging.getLogger("arquantix.security.zero_trust")


def should_persist_decision(result: Dict[str, Any], action: str) -> bool:
    if not result.get("allow", True):
        return True
    if result.get("require_step_up"):
        return True
    if result.get("action_taken") in ("deny", "restrict", "step_up"):
        return True
    sensitive_prefixes = (
        "auth.revoke_all",
        "kyc.",
        "custody.",
        "security.admin",
        "crypto.sensitive_decrypt",
        "admin.list_admins",
    )
    if any(action == p or action.startswith(p) for p in sensitive_prefixes):
        return True
    return False


def persist_security_decision(
    db: Session,
    *,
    context: RequestSecurityContext,
    result: Dict[str, Any],
    action: str,
    resource: str,
) -> Optional[AuthSecurityDecision]:
    if not should_persist_decision(result, action):
        return None
    sid = None
    if context.session_id:
        try:
            sid = uuid.UUID(context.session_id)
        except ValueError:
            sid = None
    row = AuthSecurityDecision(
        id=uuid.uuid4(),
        user_id=context.user_id,
        session_id=sid,
        device_id=context.device_id[:128] if context.device_id else None,
        action=action[:256],
        resource=resource[:512],
        allow=bool(result.get("allow")),
        require_step_up=bool(result.get("require_step_up")),
        deny_reason=(result.get("deny_reason") or None),
        policy_id=str(result.get("policy_id") or "unknown")[:128],
        context_snapshot_json=_safe_snapshot(context),
    )
    db.add(row)
    try:
        db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("zero_trust decision persist failed: %s", exc)
        return None
    logger.info(
        "zero_trust.decision %s",
        {
            "policy_id": row.policy_id,
            "allow": row.allow,
            "action": action,
            "user_id": context.user_id,
        },
    )
    return row


def _safe_snapshot(ctx: RequestSecurityContext) -> Dict[str, Any]:
    try:
        d = ctx.snapshot_dict()
        return json.loads(json.dumps(d, default=str))
    except Exception:
        return {}
