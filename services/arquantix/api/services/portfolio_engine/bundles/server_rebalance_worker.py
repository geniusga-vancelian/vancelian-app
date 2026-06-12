"""Pilote serveur d'un rééquilibrage portefeuille (worker, sans navigateur).

Réutilise **intégralement** l'orchestrateur existant :

  - ``rebalancing_portfolio(trigger="server")``        → démarre un cycle (guard PE +
    lock global batch + drift/plan + executor) ; chaque leg est **signé côté serveur**
    via le trigger ``server`` greffé sur ``BundleRebalanceExecutor``.
  - ``resume_rebalancing_portfolio(trigger="server")`` → reprend un cycle RUNNING
    (poll d'un leg SUBMITTED, re-planification si plan_hash a dérivé, leg suivant).

Aucune nouvelle file ni nouvel orchestrateur : le worker n'est qu'un *appelant gated*.

Garde-fous (fail-closed) :
  - flag global ``LIFI_REBALANCE_WORKER_ENABLED`` (défaut OFF)
  - allowlist par personne (``lifi_rebalance_worker_enabled_for_person``)
  - si le wallet n'est pas délégué, l'executor retombe leg par leg sur ``expired``
    (jamais de signature client forcée côté serveur).
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _resolve_person_id(db: Session, client_id: UUID) -> UUID | None:
    from services.portfolio_engine.clients.models import Client

    row = db.query(Client).filter(Client.id == client_id).first()
    return row.person_id if row is not None else None


def run_server_side_rebalance_for_portfolio(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> dict[str, Any]:
    """Démarre ou reprend un rééquilibrage **100 % serveur** pour un portefeuille.

    Idempotent : si un cycle RUNNING existe déjà, on **reprend** (jamais de double
    démarrage — réutilise l'idempotence par ``plan_hash`` de l'executor). Retourne le
    payload de rééquilibrage (``v3_status`` RUNNING/terminal) ou un descriptif ``skipped``.
    """
    person_id = _resolve_person_id(db, client_id)
    if person_id is None:
        return {
            "skipped": True,
            "reason": "client_has_no_person_id",
            "portfolio_id": str(portfolio_id),
        }

    from services.lifi.orchestrator_allowlist import (
        lifi_rebalance_worker_enabled_for_person,
    )

    if not lifi_rebalance_worker_enabled_for_person(db, person_id):
        return {
            "skipped": True,
            "reason": "rebalance_worker_not_enabled_for_person",
            "portfolio_id": str(portfolio_id),
        }

    from .rebalance_executor import find_running_v3_rebalance_execution
    from .rebalancing_portfolio import (
        RebalancingPortfolioError,
        rebalancing_portfolio,
        resume_rebalancing_portfolio,
        should_use_portfolio_rebalancing,
    )

    running = find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio_id))
    try:
        if running is not None:
            return resume_rebalancing_portfolio(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                trigger="server",
            )

        if not should_use_portfolio_rebalancing(
            db, client_id=client_id, portfolio_id=portfolio_id,
        ):
            return {
                "skipped": True,
                "reason": "no_rebalance_required",
                "portfolio_id": str(portfolio_id),
            }

        return rebalancing_portfolio(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            trigger="server",
        )
    except RebalancingPortfolioError as exc:
        logger.warning(
            "server_rebalance.failed portfolio=%s code=%s",
            portfolio_id,
            getattr(exc, "code", ""),
        )
        return {
            "skipped": False,
            "error": getattr(exc, "code", "rebalancing_error"),
            "portfolio_id": str(portfolio_id),
        }
