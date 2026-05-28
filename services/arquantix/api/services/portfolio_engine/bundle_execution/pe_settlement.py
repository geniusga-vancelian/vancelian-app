"""Mise à jour des ``pe_position_atoms`` — uniquement après swap LI.FI confirmé."""
from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
logger = logging.getLogger(__name__)


def _orchestrator():
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    return BundleOrchestrator


class BundlePeSettlementError(Exception):
    pass


def apply_allocation_leg_atoms_lifi_spot_only(
    db: Session,
    *,
    portfolio_id: UUID,
    target_instrument_id: UUID,
    crypto_received: Decimal,
    cost_basis_eur: Decimal,
) -> None:
    """DEPRECATED — préférer ``apply_allocation_leg_atoms`` (fund-first + débit cash leg)."""
    if crypto_received <= 0:
        raise BundlePeSettlementError("crypto_received_must_be_positive")
    _orchestrator()._sync_pe_position(
        db,
        portfolio_id,
        target_instrument_id,
        crypto_received,
        cost_basis_eur,
    )


def apply_allocation_leg_atoms(
    db: Session,
    *,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
    target_instrument_id: UUID,
    entry_asset_consumed: Decimal,
    crypto_received: Decimal,
    cost_basis_eur: Decimal,
) -> None:
    """Crédite spot + débite cash leg après confirmation on-chain."""
    if crypto_received <= 0:
        raise BundlePeSettlementError("crypto_received_must_be_positive")
    _orchestrator()._sync_pe_position(
        db,
        portfolio_id,
        target_instrument_id,
        crypto_received,
        cost_basis_eur,
    )
    _orchestrator()._debit_cash_leg(
        db,
        portfolio_id,
        entry_instrument_id,
        entry_asset_consumed,
        cost_basis_eur,
    )


def apply_rebalance_sell_atoms(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    entry_instrument_id: UUID,
    sell_qty: Decimal,
    entry_received: Decimal,
    cost_basis_eur: Decimal,
) -> None:
    from services.portfolio_engine.bundles.rebalance import BundleRebalanceOrchestrator as _Rebal

    _Rebal._debit_spot_atom(
        db, portfolio_id, instrument_id, sell_qty, cost_basis_eur,
    )
    _orchestrator()._credit_cash_leg(
        db, portfolio_id, entry_instrument_id, entry_received, cost_basis_eur,
    )


def apply_rebalance_buy_atoms(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    entry_instrument_id: UUID,
    entry_spent: Decimal,
    crypto_received: Decimal,
    cost_basis_eur: Decimal,
) -> None:
    _orchestrator()._sync_pe_position(
        db, portfolio_id, instrument_id, crypto_received, cost_basis_eur,
    )
    _orchestrator()._debit_cash_leg(
        db, portfolio_id, entry_instrument_id, entry_spent, cost_basis_eur,
    )


def credit_initial_cash_leg(
    db: Session,
    *,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
    quantity: Decimal,
    cost_basis: Decimal,
) -> None:
    """Crédite le cash leg après vérification funding (direct entry on-chain)."""
    _orchestrator()._credit_cash_leg(
        db, portfolio_id, entry_instrument_id, quantity, cost_basis,
    )


def swap_confirmed(swap) -> bool:
    return getattr(swap, "status", None) == SwapSessionStatus.CONFIRMED.value
