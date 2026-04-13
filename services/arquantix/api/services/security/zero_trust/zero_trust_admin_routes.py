"""Endpoints admin : politiques Zero Trust, évaluation, journal des décisions."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from auth import get_current_user, oauth2_scheme
from database import AdminUser, AuthSecurityDecision, get_db
from services.security.zero_trust.request_security_context import build_request_security_context
from services.security.zero_trust.security_policy_engine import evaluate_security_policy, list_policy_definitions

router = APIRouter(prefix="/admin/security", tags=["admin-zero-trust"])


def _require_security_admin(user: AdminUser) -> None:
    role = (getattr(user, "zero_trust_role", None) or "admin").lower()
    if role == "readonly":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rôle readonly : accès refusé.")


@router.get("/policies")
def get_policies(
    current_user: AdminUser = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_security_admin(current_user)
    return list_policy_definitions()


@router.get("/policies/evaluate")
def evaluate_policy_for_current_context(
    request: Request,
    action: str = Query(..., description="Identifiant d’action (ex. kyc.read)"),
    resource: str = Query("*", description="Ressource logique"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> Dict[str, Any]:
    _require_security_admin(current_user)
    ctx = build_request_security_context(
        db=db,
        request=request,
        user=current_user,
        access_token=token,
        device_header=x_device_id,
    )
    return evaluate_security_policy(ctx, action, resource)


@router.post("/policies/reload")
def reload_policies_stub(
    current_user: AdminUser = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Les règles sont définies en code (``security_policy_engine``).
    Évolution : charger depuis DB/YAML + invalidation de cache.
    """
    _require_security_admin(current_user)
    return {
        "ok": "true",
        "message": "Aucun rechargement dynamique : politique codée. Redéployer l’API pour modifier les règles.",
    }


@router.get("/decisions")
def list_security_decisions(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> Dict[str, List[Dict[str, Any]]]:
    _require_security_admin(current_user)
    rows = (
        db.query(AuthSecurityDecision)
        .order_by(AuthSecurityDecision.created_at.desc())
        .limit(limit)
        .all()
    )
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": str(r.id),
                "user_id": r.user_id,
                "session_id": str(r.session_id) if r.session_id else None,
                "device_id": r.device_id,
                "action": r.action,
                "resource": r.resource,
                "allow": r.allow,
                "require_step_up": r.require_step_up,
                "deny_reason": r.deny_reason,
                "policy_id": r.policy_id,
                "context_snapshot_json": r.context_snapshot_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return {"data": out, "total": len(out)}
