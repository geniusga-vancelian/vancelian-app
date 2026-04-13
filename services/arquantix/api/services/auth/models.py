"""Auth context model for identity/KYC endpoints."""
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class AuthContext(BaseModel):
    """Authenticated request context.

    Resolved from JWT token. Carries the user's identity and their
    linked person/client IDs for ownership checks.
    """
    user_id: int
    email: Optional[str] = None
    role: str = "user"
    zero_trust_role: str = "admin"
    person_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    jwt_sub_typ: Optional[Literal["user_id"]] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
