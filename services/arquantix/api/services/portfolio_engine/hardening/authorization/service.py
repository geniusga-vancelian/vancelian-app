"""Authorization / Ownership Scoping Service.

Checks whether an actor can access a given portfolio or client resource
based on ownership rules, not just role.

Comparison: str(portfolio.client_id) == actor.actor_id
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..security.context import ActorContext
from .repository import AdvisorClientAssignmentRepository

logger = logging.getLogger(__name__)

_BYPASS_ROLES = {"ops", "admin", "system"}

_assign_repo = AdvisorClientAssignmentRepository()


class AuthorizationService:

    def can_access_portfolio(
        self, db: Session, actor: ActorContext, portfolio_id: UUID,
    ) -> bool:
        from ...portfolios.models import Portfolio

        if actor.has_any_role(*_BYPASS_ROLES):
            return True

        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            return False

        return self._can_access_client_id(db, actor, portfolio.client_id)

    def can_access_portfolio_obj(
        self, db: Session, actor: ActorContext, portfolio,
    ) -> bool:
        if actor.has_any_role(*_BYPASS_ROLES):
            return True
        return self._can_access_client_id(db, actor, portfolio.client_id)

    def can_access_client(
        self, db: Session, actor: ActorContext, client_id: UUID,
    ) -> bool:
        if actor.has_any_role(*_BYPASS_ROLES):
            return True
        return self._can_access_client_id(db, actor, client_id)

    def get_accessible_client_ids_for_advisor(
        self, db: Session, actor_id: str,
    ) -> list[UUID]:
        return _assign_repo.get_active_client_ids(db, actor_id)

    def _can_access_client_id(
        self, db: Session, actor: ActorContext, client_id: UUID,
    ) -> bool:
        if actor.has_role("client"):
            return str(client_id) == actor.actor_id

        if actor.has_role("advisor"):
            if actor.actor_id is None:
                return False
            assigned = _assign_repo.get_active_client_ids(db, actor.actor_id)
            return client_id in assigned

        return False
