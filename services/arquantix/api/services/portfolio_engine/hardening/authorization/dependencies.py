"""Ownership scoping dependencies (Authorization).

These are independent from RBAC role guards.
They enforce data-level authorization: which resource can this actor access.

Usage in endpoint:
    portfolio = Depends(require_portfolio_access)
"""
import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from ..security.context import ActorContext
from ..security.dependencies import get_actor_context
from ..audit_service import AuditService
from .service import AuthorizationService

logger = logging.getLogger(__name__)

_auth = AuthorizationService()
_audit = AuditService()


def require_portfolio_access(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
):
    """Load portfolio, check ownership, return Portfolio object."""
    from ...portfolios.models import Portfolio

    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )

    if not _auth.can_access_portfolio_obj(db, actor, portfolio):
        try:
            _audit.log_failure(
                db,
                entity_type="portfolio",
                entity_id=str(portfolio_id),
                action="portfolio_access_denied",
                error="ownership_check_failed",
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                metadata={"roles": actor.roles},
            )
            db.flush()
        except Exception:
            logger.debug("Failed to log access denial audit event", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient access to this portfolio",
        )

    return portfolio


def require_client_access(
    client_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
):
    """Check client ownership, return Client object."""
    from ...clients.models import Client

    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    if not _auth.can_access_client(db, actor, client_id):
        try:
            _audit.log_failure(
                db,
                entity_type="client",
                entity_id=str(client_id),
                action="client_access_denied",
                error="ownership_check_failed",
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                metadata={"roles": actor.roles},
            )
            db.flush()
        except Exception:
            logger.debug("Failed to log access denial audit event", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient access to this client",
        )

    return client


def require_position_portfolio_access(
    position_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
):
    """Resolve ``position_id`` → portfolio, enforce same ownership as ``require_portfolio_access``."""
    from ...positions.models import PositionAtom
    from ...portfolios.models import Portfolio

    pos = db.query(PositionAtom).filter(PositionAtom.id == position_id).first()
    if pos is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found",
        )

    portfolio = db.query(Portfolio).filter(Portfolio.id == pos.portfolio_id).first()
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {pos.portfolio_id} not found",
        )

    if not _auth.can_access_portfolio_obj(db, actor, portfolio):
        try:
            _audit.log_failure(
                db,
                entity_type="position",
                entity_id=str(position_id),
                action="position_portfolio_access_denied",
                error="ownership_check_failed",
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                metadata={"roles": actor.roles, "portfolio_id": str(portfolio.id)},
            )
            db.flush()
        except Exception:
            logger.debug("Failed to log access denial audit event", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient access to this position",
        )

    return pos


def require_orchestration_run_portfolio_access(
    run_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
):
    """Resolve orchestration run → portfolio, enforce ownership (closes IDOR on run GET)."""
    from ...orchestrator.models import OrchestrationRun
    from ...portfolios.models import Portfolio

    run = db.query(OrchestrationRun).filter(OrchestrationRun.id == run_id).first()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OrchestrationRun {run_id} not found",
        )

    portfolio = db.query(Portfolio).filter(Portfolio.id == run.portfolio_id).first()
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {run.portfolio_id} not found",
        )

    if not _auth.can_access_portfolio_obj(db, actor, portfolio):
        try:
            _audit.log_failure(
                db,
                entity_type="orchestration_run",
                entity_id=str(run_id),
                action="orchestration_run_access_denied",
                error="ownership_check_failed",
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                metadata={"roles": actor.roles, "portfolio_id": str(portfolio.id)},
            )
            db.flush()
        except Exception:
            logger.debug("Failed to log access denial audit event", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient access to this orchestration run",
        )

    return run
