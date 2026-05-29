"""Admin read-only — réconciliation shadow bundle ledger (Phase 4A.5)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow
from services.portfolio_engine.bundle_ledger.admin_payload import enrich_admin_reconciliation_payload
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops
from services.portfolio_engine.portfolios.models import Portfolio

bundle_ledger_admin_router = APIRouter(
    prefix="/api/admin/bundles",
    tags=["bundle-ledger-admin"],
)
_guard = require_admin_or_ops()


@bundle_ledger_admin_router.get("/{portfolio_id}/ledger/reconciliation")
def admin_bundle_ledger_reconciliation(
    portfolio_id: UUID,
    person_id: Optional[UUID] = Query(None, description="UUID person (déduit du portfolio si absent)"),
    batch_id: Optional[str] = Query(None, description="Filtrer par batch"),
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Réconciliation shadow ledger vs PE — admin/ops uniquement, read-only."""
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .first()
    )
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="portfolio_not_found")

    resolved_person_id = person_id
    if resolved_person_id is None:
        client = db.query(Client).filter(Client.id == portfolio.client_id).first()
        if client is None or client.person_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="person_id_required",
            )
        resolved_person_id = client.person_id

    try:
        payload = reconcile_bundle_ledger_shadow(
            db,
            person_id=resolved_person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        return enrich_admin_reconciliation_payload(payload, portfolio=portfolio)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
