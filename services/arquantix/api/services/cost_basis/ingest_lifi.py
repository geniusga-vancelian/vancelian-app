"""Ingestion Li.FI / Privy → cost_basis_executions (Mon Trading / direct)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from services.cost_basis.ingest_lifi_core import ingest_lifi_swap_cost_basis
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
    swap_has_strong_bundle_batch_context,
)


def ingest_lifi_swap_settlement(
    db: Session,
    swap,
    *,
    wallet,
    amount_out: Decimal,
) -> int:
    """Produit les faits d'exécution après règlement ledger Li.FI. Retourne le nombre de lignes créées."""
    if is_bundle_internal_swap(swap) or swap_has_strong_bundle_batch_context(swap):
        return 0

    return ingest_lifi_swap_cost_basis(
        db,
        swap,
        wallet=wallet,
        amount_out=amount_out,
        portfolio_scope="direct",
        portfolio_id=None,
        provider_source="lifi",
        provider_id_prefix="lifi",
    )
