"""Mise à jour des ``pe_position_atoms`` — uniquement après swap LI.FI confirmé."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
logger = logging.getLogger(__name__)


def _orchestrator():
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    return BundleOrchestrator


class BundlePeSettlementError(Exception):
    pass


def _ledger_context(
    ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    return ledger if isinstance(ledger, dict) else {}


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
    ledger: dict[str, Any] | None = None,
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

    ctx = _ledger_context(ledger)
    person_id = ctx.get("person_id")
    if person_id is not None:
        from services.portfolio_engine.bundle_ledger.service import record_allocation_buy

        record_allocation_buy(
            db,
            person_id=UUID(str(person_id)),
            bundle_portfolio_id=portfolio_id,
            target_instrument_id=target_instrument_id,
            target_asset_symbol=str(ctx.get("target_asset_symbol") or ctx.get("to_asset") or ""),
            crypto_received=crypto_received,
            entry_asset_consumed=entry_asset_consumed,
            entry_instrument_id=entry_instrument_id,
            entry_asset_symbol=str(ctx.get("entry_asset_symbol") or ctx.get("from_asset") or ""),
            batch_id=ctx.get("batch_id"),
            leg_id=ctx.get("leg_id"),
            swap_id=UUID(str(ctx["swap_id"])) if ctx.get("swap_id") else None,
            cost_basis_eur=cost_basis_eur,
            planned_entry_consumed=(
                Decimal(str(ctx["planned_amount_in"]))
                if ctx.get("planned_amount_in") is not None
                else None
            ),
            planned_crypto_received=(
                Decimal(str(ctx["planned_amount_out"]))
                if ctx.get("planned_amount_out") is not None
                else None
            ),
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
    ledger: dict[str, Any] | None = None,
) -> None:
    from services.portfolio_engine.bundles.rebalance import BundleRebalanceOrchestrator as _Rebal

    _Rebal._debit_spot_atom(
        db, portfolio_id, instrument_id, sell_qty, cost_basis_eur,
    )
    _orchestrator()._credit_cash_leg(
        db, portfolio_id, entry_instrument_id, entry_received, cost_basis_eur,
    )

    ctx = _ledger_context(ledger)
    person_id = ctx.get("person_id")
    if person_id is not None:
        from services.portfolio_engine.bundle_ledger.service import record_rebalance

        record_rebalance(
            db,
            person_id=UUID(str(person_id)),
            bundle_portfolio_id=portfolio_id,
            side="sell",
            instrument_id=instrument_id,
            asset_symbol=str(ctx.get("from_asset") or ctx.get("asset_symbol") or ""),
            quantity=sell_qty,
            entry_instrument_id=entry_instrument_id,
            entry_asset_symbol=str(ctx.get("to_asset") or ctx.get("entry_asset_symbol") or ""),
            entry_amount=entry_received,
            batch_id=ctx.get("batch_id"),
            leg_id=ctx.get("leg_id"),
            swap_id=UUID(str(ctx["swap_id"])) if ctx.get("swap_id") else None,
            cost_basis_eur=cost_basis_eur,
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
    ledger: dict[str, Any] | None = None,
) -> None:
    _orchestrator()._sync_pe_position(
        db, portfolio_id, instrument_id, crypto_received, cost_basis_eur,
    )
    _orchestrator()._debit_cash_leg(
        db, portfolio_id, entry_instrument_id, entry_spent, cost_basis_eur,
    )

    ctx = _ledger_context(ledger)
    person_id = ctx.get("person_id")
    if person_id is not None:
        from services.portfolio_engine.bundle_ledger.service import record_rebalance

        record_rebalance(
            db,
            person_id=UUID(str(person_id)),
            bundle_portfolio_id=portfolio_id,
            side="buy",
            instrument_id=instrument_id,
            asset_symbol=str(ctx.get("to_asset") or ctx.get("asset_symbol") or ""),
            quantity=crypto_received,
            entry_instrument_id=entry_instrument_id,
            entry_asset_symbol=str(ctx.get("from_asset") or ctx.get("entry_asset_symbol") or ""),
            entry_amount=entry_spent,
            batch_id=ctx.get("batch_id"),
            leg_id=ctx.get("leg_id"),
            swap_id=UUID(str(ctx["swap_id"])) if ctx.get("swap_id") else None,
            cost_basis_eur=cost_basis_eur,
        )


def apply_withdraw_sell_atoms(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    entry_instrument_id: UUID,
    sell_qty: Decimal,
    entry_received: Decimal,
    cost_basis_eur: Decimal,
    ledger: dict[str, Any] | None = None,
) -> None:
    """Vente bundle confirmée : spot → cash leg (+ settlement Privy en amont)."""
    from services.portfolio_engine.bundles.rebalance import BundleRebalanceOrchestrator as _Rebal

    _Rebal._debit_spot_atom(
        db, portfolio_id, instrument_id, sell_qty, cost_basis_eur,
    )
    _orchestrator()._credit_cash_leg(
        db, portfolio_id, entry_instrument_id, entry_received, cost_basis_eur,
    )

    ctx = _ledger_context(ledger)
    person_id = ctx.get("person_id")
    if person_id is not None:
        from services.portfolio_engine.bundle_ledger.service import record_allocation_sell

        record_allocation_sell(
            db,
            person_id=UUID(str(person_id)),
            bundle_portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            asset_symbol=str(ctx.get("from_asset") or ""),
            sell_qty=sell_qty,
            entry_received=entry_received,
            entry_instrument_id=entry_instrument_id,
            entry_asset_symbol=str(ctx.get("to_asset") or ctx.get("entry_asset_symbol") or ""),
            batch_id=ctx.get("batch_id"),
            leg_id=ctx.get("leg_id"),
            swap_id=UUID(str(ctx["swap_id"])) if ctx.get("swap_id") else None,
            withdraw_sell=True,
            cost_basis_eur=cost_basis_eur,
        )


def apply_withdraw_release_atoms(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
    entry_asset: str,
    amount: Decimal,
    batch_id: str,
) -> None:
    """Release comptable cash leg → direct_portfolio (Privy inchangé)."""
    from services.portfolio_engine.bundle_execution.bundle_funding import (
        release_bundle_cash_leg_to_self_trading,
    )

    release_bundle_cash_leg_to_self_trading(
        db,
        client_id=client_id,
        person_id=None,
        portfolio_id=portfolio_id,
        entry_asset=entry_asset,
        entry_instrument_id=entry_instrument_id,
        amount=amount,
        batch_id=batch_id,
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
