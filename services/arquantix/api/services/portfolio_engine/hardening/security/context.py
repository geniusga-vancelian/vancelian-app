"""Actor context for RBAC (Hardening Subphase 5).

Lightweight abstraction representing the current request actor.
Extracted from headers in v1; can be replaced by JWT/IdP later.
"""
from typing import Optional

from pydantic import BaseModel, Field


class ActorContext(BaseModel):
    actor_type: str = "system"
    actor_id: Optional[str] = None
    roles: list[str] = Field(default_factory=list)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        return bool(set(self.roles) & set(roles))

    @property
    def is_system(self) -> bool:
        return self.actor_type == "system"
