"""Ingestion Li.FI bundle (legs allocation / rebalance) → cost_basis_executions."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.ingest_lifi_core import ingest_lifi_swap_cost_basis
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    bundle_portfolio_id_from_swap,
    is_bundle_internal_swap,
)


def ingest_bundle_lifi_swap_settlement(
    db: Session,
    swap,
    *,
    wallet,
    amount_out: Decimal,
    portfolio_id: UUID,
) -> int:
    """Ingère le PRU scoped bundle après règlement d'un leg Li.FI interne."""
    if not is_bundle_internal_swap(swap):
        return 0

    pid = bundle_portfolio_id_from_swap(swap)
    if pid is not None and str(pid) != str(portfolio_id):
        return 0

    return ingest_lifi_swap_cost_basis(
        db,
        swap,
        wallet=wallet,
        amount_out=amount_out,
        portfolio_scope="bundle",
        portfolio_id=portfolio_id,
        provider_source="bundle_lifi",
        provider_id_prefix="bundle-lifi",
    )
