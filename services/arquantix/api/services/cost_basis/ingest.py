"""Ingestion canonique — point d'entrée unique."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.repository import CostBasisExecutionRepository
from services.cost_basis.valuation import FrozenExecutionValuation

logger = logging.getLogger(__name__)

_repo = CostBasisExecutionRepository()


def record_execution(
    db: Session,
    *,
    client_id: UUID,
    person_id: Optional[UUID],
    position_asset: str,
    event_kind: str,
    quantity: Decimal,
    valuation: FrozenExecutionValuation,
    provider_source: str,
    provider_execution_id: str,
    executed_at: datetime,
    tx_hash: Optional[str] = None,
    counterparty_asset: Optional[str] = None,
    portfolio_scope: Optional[str] = None,
    portfolio_id: Optional[UUID] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[UUID]:
    """Enregistre une exécution (idempotent). Retourne l'id ou None si doublon."""
    existing = _repo.find_by_provider(
        db,
        provider_source=provider_source,
        provider_execution_id=provider_execution_id,
    )
    if existing is not None:
        return None

    row = _repo.create(
        db,
        client_id=client_id,
        person_id=person_id,
        position_asset=position_asset,
        event_kind=event_kind,
        quantity=quantity,
        valuation=valuation,
        provider_source=provider_source,
        provider_execution_id=provider_execution_id,
        tx_hash=tx_hash,
        counterparty_asset=counterparty_asset,
        portfolio_scope=portfolio_scope,
        portfolio_id=portfolio_id,
        executed_at=executed_at,
        metadata=metadata,
    )
    return row.id
