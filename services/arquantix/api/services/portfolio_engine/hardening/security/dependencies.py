"""FastAPI dependencies for RBAC (Hardening Subphase 5).

Headers used in v1:
  X-Actor-Type   — actor type (client, advisor, ops, admin, system)
  X-Actor-Id     — actor identifier
  X-Actor-Roles  — comma-separated role list

Fallback (no headers): actor_type="system", actor_id=None, roles=[]
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from .context import ActorContext


def get_actor_context(
    x_actor_type: Optional[str] = Header(None, alias="X-Actor-Type"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    x_actor_roles: Optional[str] = Header(None, alias="X-Actor-Roles"),
) -> ActorContext:
    actor_type = x_actor_type or "system"
    actor_id = x_actor_id or None
    roles: list[str] = []
    if x_actor_roles:
        roles = [r.strip() for r in x_actor_roles.split(",") if r.strip()]
    return ActorContext(actor_type=actor_type, actor_id=actor_id, roles=roles)


class _RoleGuard:
    """Callable dependency that enforces role requirements."""

    def __init__(self, *, required_roles: list[str], require_all: bool = False):
        self._required = required_roles
        self._require_all = require_all

    def __call__(
        self, actor: ActorContext = Depends(get_actor_context),
    ) -> ActorContext:
        if self._require_all:
            if not all(actor.has_role(r) for r in self._required):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: requires all of {self._required}",
                )
        else:
            if not actor.has_any_role(*self._required):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: requires any of {self._required}",
                )
        return actor


def require_any_role(*roles: str) -> _RoleGuard:
    return _RoleGuard(required_roles=list(roles))


def require_roles(*roles: str) -> _RoleGuard:
    return _RoleGuard(required_roles=list(roles), require_all=True)


def require_admin_or_ops() -> _RoleGuard:
    return require_any_role("admin", "ops")


def require_internal_or_admin() -> _RoleGuard:
    return require_any_role("admin", "system")
