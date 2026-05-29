"""Logique partagée d'ingestion Li.FI → cost_basis_executions (direct ou bundle)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.ingest import record_execution
from services.cost_basis.valuation import (
    build_crypto_cross_valuation,
    build_frozen_valuation,
    classify_native_quote,
)

logger = logging.getLogger(__name__)


def _dec(v: object) -> Decimal:
    return Decimal(str(v))


def _executed_at(swap) -> datetime:
    ts = swap.confirmed_at or swap.created_at
    if ts is None:
        return datetime.now(timezone.utc)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def ingest_lifi_swap_cost_basis(
    db: Session,
    swap,
    *,
    wallet,
    amount_out: Decimal,
    portfolio_scope: str,
    portfolio_id: Optional[UUID] = None,
    provider_source: str,
    provider_id_prefix: str,
) -> int:
    """Produit les faits d'exécution après règlement Li.FI (scope direct ou bundle)."""
    client_id = wallet.pe_client_id
    if client_id is None:
        logger.warning("cost_basis.lifi_skip: missing pe_client_id swap=%s", swap.id)
        return 0

    person_id = getattr(swap, "person_id", None) or wallet.person_id
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    amount_in = _dec(swap.amount_in)
    fee = _dec(swap.vancelian_fee) if getattr(swap, "vancelian_fee", None) else Decimal("0")
    executed = _executed_at(swap)
    tx_hash = str(swap.tx_hash or "").strip().lower() or None
    swap_id = str(swap.id)
    created = 0

    meta_base: dict[str, Any] = {
        "lifi_swap_id": swap_id,
        "from_asset": from_asset,
        "to_asset": to_asset,
        "portfolio_scope": portfolio_scope,
    }
    if portfolio_id is not None:
        meta_base["portfolio_id"] = str(portfolio_id)

    from_kind = classify_native_quote(from_asset)

    if from_kind != "crypto":
        valuation_acquire = build_frozen_valuation(
            db,
            position_asset=to_asset,
            quantity=amount_out,
            quote_asset=from_asset,
            quote_amount=amount_in,
            fee_quote_amount=fee,
            executed_at=executed,
        )
        if record_execution(
            db,
            client_id=client_id,
            person_id=person_id,
            position_asset=to_asset,
            event_kind="acquisition",
            quantity=amount_out,
            valuation=valuation_acquire,
            provider_source=provider_source,
            provider_execution_id=f"{provider_id_prefix}:{swap_id}:acquisition:{to_asset}",
            executed_at=executed,
            tx_hash=tx_hash,
            counterparty_asset=from_asset,
            portfolio_scope=portfolio_scope,
            portfolio_id=portfolio_id,
            metadata={**meta_base, "leg": "acquisition"},
        ):
            created += 1
    else:
        valuation_dispose = build_crypto_cross_valuation(
            db,
            position_asset=from_asset,
            quantity=amount_in,
            from_asset=from_asset,
            from_amount=amount_in,
            fee_from_amount=fee,
            executed_at=executed,
        )
        if record_execution(
            db,
            client_id=client_id,
            person_id=person_id,
            position_asset=from_asset,
            event_kind="disposal",
            quantity=amount_in,
            valuation=valuation_dispose,
            provider_source=provider_source,
            provider_execution_id=f"{provider_id_prefix}:{swap_id}:disposal:{from_asset}",
            executed_at=executed,
            tx_hash=tx_hash,
            counterparty_asset=to_asset,
            portfolio_scope=portfolio_scope,
            portfolio_id=portfolio_id,
            metadata={**meta_base, "leg": "disposal"},
        ):
            created += 1

        valuation_acquire = build_crypto_cross_valuation(
            db,
            position_asset=to_asset,
            quantity=amount_out,
            from_asset=from_asset,
            from_amount=amount_in,
            fee_from_amount=Decimal("0"),
            executed_at=executed,
        )
        if record_execution(
            db,
            client_id=client_id,
            person_id=person_id,
            position_asset=to_asset,
            event_kind="acquisition",
            quantity=amount_out,
            valuation=valuation_acquire,
            provider_source=provider_source,
            provider_execution_id=f"{provider_id_prefix}:{swap_id}:acquisition:{to_asset}",
            executed_at=executed,
            tx_hash=tx_hash,
            counterparty_asset=from_asset,
            portfolio_scope=portfolio_scope,
            portfolio_id=portfolio_id,
            metadata={**meta_base, "leg": "acquisition"},
        ):
            created += 1

    return created
