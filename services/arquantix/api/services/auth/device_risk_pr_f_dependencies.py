"""PR F — FastAPI Depends : score risque + allow / step_up / block sur routes sensibles."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import get_current_user, oauth2_scheme
from database import AdminUser, get_db
from services.auth.device_risk_engine_pr_f import (
    evaluate_pr_f_for_request,
    resolve_session_for_pr_f,
    touch_user_device_profile_for_risk,
)
from services.auth.device_risk_engine_pr_f2 import update_user_risk_baseline_from_observation
from services.auth.refresh_session import LEGACY_UNKNOWN_DEVICE, normalize_device_id
from services.security.device_reputation.device_reputation_service import resolve_device_hash_from_request
from services.security.security_env import (
    is_device_risk_advanced_baseline_enabled,
    is_device_risk_baseline_enabled,
    is_device_risk_engine_pr_f_enabled,
    is_device_intent_engine_enabled,
)

logger = logging.getLogger("arquantix.auth.device_risk_pr_f")


def require_low_risk_action() -> Callable:
    """
    Si ``DEVICE_RISK_ENGINE_PR_F_ENABLED`` : évalue le risque et met à jour le profil device.

    - ``allow`` : OK (profil ``last_ip`` / ``last_country`` / ``last_seen_at`` mis à jour).
    - ``step_up`` : 403 ``device_risk_step_up``.
    - ``block`` : 403 ``device_risk_blocked``.

    Sinon : no-op (rétrocompat, zéro requête métier supplémentaire hors Depends standard).
    """

    async def _dep(
        request: Request,
        db: Session = Depends(get_db),
        current_user: AdminUser = Depends(get_current_user),
        token: str = Depends(oauth2_scheme),
        x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    ) -> None:
        if not is_device_risk_engine_pr_f_enabled():
            return

        did = normalize_device_id(x_device_id)
        if did == LEGACY_UNKNOWN_DEVICE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "device_risk_blocked",
                    "step_up": False,
                    "risk_score": 100,
                    "risk_reason": ["missing_x_device_id"],
                    "message": "X-Device-ID requis pour l’évaluation du risque.",
                },
            )

        fp = request.headers.get("x-fingerprint-hash") or request.headers.get("X-Fingerprint-Hash")
        fp_norm = (str(fp).strip()[:64] if fp else None) or None
        device_hash = resolve_device_hash_from_request(request, did, fp_norm)

        result = evaluate_pr_f_for_request(
            db,
            request=request,
            user_id=current_user.id,
            token=token,
            device_id_raw=x_device_id,
        )
        score = result.score
        decision = result.decision
        risk_reason = list(result.risk_reasons)

        if is_device_intent_engine_enabled():
            from services.auth.device_intent_engine import log_intent_event
            from services.auth.device_risk_engine_pr_f3 import infer_risk_action_type

            log_intent_event(
                db,
                user_id=current_user.id,
                device_id=did,
                action_type=infer_risk_action_type(request),
                risk_decision=result.decision,
            )

        ip = None
        xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        if xff:
            ip = xff.split(",")[0].strip()[:45]
        elif request.client:
            ip = (request.client.host or "")[:45] or None

        country = (
            request.headers.get("cf-ipcountry")
            or request.headers.get("CF-IPCountry")
            or request.headers.get("x-country-code")
            or ""
        )
        country = str(country).strip().upper()[:8] if country else None

        touch_user_device_profile_for_risk(
            db,
            user_id=current_user.id,
            device_hash=device_hash,
            device_id_normalized=did,
            ip=ip,
            country=country,
        )

        if decision == "allow" and (
            is_device_risk_baseline_enabled() or is_device_risk_advanced_baseline_enabled()
        ):
            sess = resolve_session_for_pr_f(db, user_id=current_user.id, token=token)
            update_user_risk_baseline_from_observation(
                db,
                user_id=current_user.id,
                ctx=result.context,
                request=request,
                session=sess,
            )

        logger.info(
            "device_risk_evaluated",
            extra={
                "event": "device_risk_evaluated",
                "user_id": current_user.id,
                "device_id": did[:24],
                "risk_score": score,
                "decision": decision,
                "risk_reason": risk_reason,
                "ip": ip,
                "country": country,
                "route": request.url.path,
            },
        )

        if decision == "allow":
            return

        if decision == "step_up":
            detail_su: dict = {
                "error": "device_risk_step_up",
                "step_up": True,
                "risk_score": score,
                "risk_reason": risk_reason,
            }
            if result.triggered_rule_name is not None:
                detail_su["rule_triggered"] = result.triggered_rule_name
            if result.triggered_rule_conditions is not None:
                detail_su["rule_conditions"] = result.triggered_rule_conditions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_su,
            )

        detail_blk: dict = {
            "error": "device_risk_blocked",
            "step_up": False,
            "risk_score": score,
            "risk_reason": risk_reason,
        }
        if result.triggered_rule_name is not None:
            detail_blk["rule_triggered"] = result.triggered_rule_name
        if result.triggered_rule_conditions is not None:
            detail_blk["rule_conditions"] = result.triggered_rule_conditions
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_blk,
        )

    return _dep
