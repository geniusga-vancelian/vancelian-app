"""En-têtes BFF custody : opérateur CMS réel vs JWT compte de service (Option B)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from starlette.requests import Request


@dataclass(frozen=True)
class CmsOperatorHeaders:
    cms_user_id: Optional[str]
    cms_user_email: Optional[str]
    cms_user_roles: Optional[str]
    request_id: Optional[str]
    x_actor_type: Optional[str]
    x_actor_id: Optional[str]


def parse_cms_operator_headers(request: Request) -> CmsOperatorHeaders:
    """Lit les en-têtes émis par le BFF Next (`custody-bff.ts`)."""

    def _h(name: str) -> Optional[str]:
        v = request.headers.get(name) or request.headers.get(name.lower())
        if v is None or str(v).strip() == "":
            return None
        return str(v).strip()

    return CmsOperatorHeaders(
        cms_user_id=_h("x-cms-user-id"),
        cms_user_email=_h("x-cms-user-email"),
        cms_user_roles=_h("x-cms-user-roles"),
        request_id=_h("x-request-id"),
        x_actor_type=_h("x-actor-type"),
        x_actor_id=_h("x-actor-id"),
    )


def custody_audit_extra(
    *,
    request: Request,
    action: str,
    person_id: Optional[str] = None,
    actor_jwt_user_id: int = 0,
) -> Dict[str, Any]:
    """Métadonnées à fusionner dans record_sensitive_action / logs structurés."""
    cms = parse_cms_operator_headers(request)
    out: Dict[str, Any] = {
        "action": action,
        "actor_jwt_user_id": actor_jwt_user_id,
        "actor_type_header": cms.x_actor_type,
        "actor_id_header": cms.x_actor_id,
        "request_id": cms.request_id,
        "cms_user_id": cms.cms_user_id,
        "cms_user_email": cms.cms_user_email,
        "cms_user_roles": cms.cms_user_roles,
    }
    if person_id:
        out["person_id"] = person_id
    return out
