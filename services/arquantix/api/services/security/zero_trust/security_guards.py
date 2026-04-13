"""Gardes FastAPI / helpers pour actions sensibles Zero Trust."""
from __future__ import annotations

from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth import authenticated_admin_core
from database import AdminUser, get_db
from services.security.zero_trust.decision_logging import persist_security_decision
from services.security.zero_trust.request_security_context import build_request_security_context
from services.security.zero_trust.security_policy_engine import auth_strength_sufficient, evaluate_security_policy

_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


def build_context_for_request(
    *,
    db: Session,
    request: Request,
    user: AdminUser,
    token: str,
    x_device_id: Optional[str],
):
    return build_request_security_context(
        db=db,
        request=request,
        user=user,
        access_token=token,
        device_header=x_device_id,
    )


def enforce_zero_trust_or_raise(
    *,
    db: Session,
    request: Request,
    user: AdminUser,
    token: str,
    action: str,
    resource: str,
    x_device_id: Optional[str] = None,
    strict_step_up: bool = True,
) -> None:
    ctx = build_context_for_request(db=db, request=request, user=user, token=token, x_device_id=x_device_id)
    result = evaluate_security_policy(ctx, action, resource)
    persist_security_decision(db, context=ctx, result=result, action=action, resource=resource)
    try:
        db.flush()
    except Exception:
        pass
    if not result.get("allow"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "zero_trust.denied",
                "message": result.get("deny_reason") or "Accès refusé par la politique de sécurité.",
                "policy_id": result.get("policy_id"),
                "require_step_up": result.get("require_step_up"),
            },
        )
    if strict_step_up and result.get("require_step_up"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "zero_trust.step_up_required",
                "message": result.get("deny_reason") or "Renforcement d’authentification requis.",
                "policy_id": result.get("policy_id"),
                "step_up": True,
                "otp_login_path": "/auth/login/email-otp/start",
            },
        )


def require_zero_trust_action(action: str, resource_fn: Optional[Callable[[Request], str]] = None):
    """
    Fabrique une dépendance FastAPI qui applique la politique après authentification.

    ``resource_fn`` optionnel : ``lambda req: f"person:{req.path_params['person_id']}"``.
    """

    def _dep(
        request: Request,
        db: Session = Depends(get_db),
        token: str = Depends(_oauth2),
        user: AdminUser = Depends(authenticated_admin_core),
        x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    ) -> AdminUser:
        res = resource_fn(request) if resource_fn else "*"
        enforce_zero_trust_or_raise(
            db=db,
            request=request,
            user=user,
            token=token,
            action=action,
            resource=res,
            x_device_id=x_device_id,
        )
        return user

    return _dep


def require_auth_strength(min_strength: str):
    """Vérifie la force d’auth du contexte (OTP, passkey, etc.)."""

    def _dep(
        request: Request,
        db: Session = Depends(get_db),
        token: str = Depends(_oauth2),
        user: AdminUser = Depends(authenticated_admin_core),
        x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    ) -> AdminUser:
        ctx = build_context_for_request(db=db, request=request, user=user, token=token, x_device_id=x_device_id)
        if not auth_strength_sufficient(min_strength, ctx.auth_strength):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "zero_trust.auth_strength_insufficient",
                    "message": f"Authentification trop faible (min: {min_strength}).",
                },
            )
        return user

    return _dep


def require_low_risk_or_step_up(action: str = "session.api_access", resource: str = "*"):
    """Refuse si risque élevé sans step-up satisfaisant (politique unifiée)."""

    def _dep(
        request: Request,
        db: Session = Depends(get_db),
        token: str = Depends(_oauth2),
        user: AdminUser = Depends(authenticated_admin_core),
        x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    ) -> AdminUser:
        enforce_zero_trust_or_raise(
            db=db,
            request=request,
            user=user,
            token=token,
            action=action,
            resource=resource,
            x_device_id=x_device_id,
            strict_step_up=True,
        )
        return user

    return _dep
