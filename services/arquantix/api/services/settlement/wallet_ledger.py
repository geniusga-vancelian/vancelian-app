"""Wallet-ledger settlement — link PositionAtoms to virtual wallets post-CONFIRMED (ADR 008)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.wallets.models import WalletContainer
from services.portfolio_engine.wallets.resolver import portfolio_scope_from_wallet
from services.trade_core.execute_trade import read_trade_wallet_context

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WalletLedgerSettleResult:
    applied: bool
    wallet_from_id: UUID | None = None
    wallet_to_id: UUID | None = None
    reason: str | None = None


def _link_atom_to_wallet(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    wallet_id: UUID,
    position_type: str,
) -> int:
    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == position_type,
            PositionAtom.status == "open",
        )
        .all()
    )
    linked = 0
    for atom in atoms:
        if atom.wallet_id is None:
            atom.wallet_id = wallet_id
            linked += 1
    if linked:
        db.flush()
    return linked


def settle_trade_wallets(
    db: Session,
    swap: PersonWalletSwap,
) -> WalletLedgerSettleResult:
    """After economic settlement, ensure PositionAtoms reference virtual wallets."""
    ctx = read_trade_wallet_context(swap)
    if ctx is None:
        return WalletLedgerSettleResult(applied=False, reason="no_wallet_context")

    wallet_from_raw = ctx.get("wallet_from_id") or ""
    wallet_to_raw = ctx.get("wallet_to_id") or ""
    if not wallet_from_raw or not wallet_to_raw:
        return WalletLedgerSettleResult(applied=False, reason="incomplete_wallet_context")

    wallet_from_id = UUID(wallet_from_raw)
    wallet_to_id = UUID(wallet_to_raw)

    wallet_from = db.query(WalletContainer).filter(WalletContainer.id == wallet_from_id).first()
    wallet_to = db.query(WalletContainer).filter(WalletContainer.id == wallet_to_id).first()
    if wallet_from is None or wallet_to is None:
        return WalletLedgerSettleResult(
            applied=False,
            reason="wallet_container_missing",
            wallet_from_id=wallet_from_id,
            wallet_to_id=wallet_to_id,
        )

    linked = 0
    if wallet_from.portfolio_id and wallet_from.instrument_id:
        pos_type = (
            PositionType.CASH
            if wallet_from.wallet_type == "cash_wallet"
            else PositionType.SPOT
        )
        linked += _link_atom_to_wallet(
            db,
            portfolio_id=wallet_from.portfolio_id,
            instrument_id=wallet_from.instrument_id,
            wallet_id=wallet_from_id,
            position_type=pos_type,
        )
    if wallet_to.portfolio_id and wallet_to.instrument_id:
        pos_type = (
            PositionType.CASH
            if wallet_to.wallet_type == "cash_wallet"
            else PositionType.SPOT
        )
        linked += _link_atom_to_wallet(
            db,
            portfolio_id=wallet_to.portfolio_id,
            instrument_id=wallet_to.instrument_id,
            wallet_id=wallet_to_id,
            position_type=pos_type,
        )

    scope_from, _ = portfolio_scope_from_wallet(db, wallet_from_id)
    logger.info(
        "wallet_ledger_settled swap=%s from=%s to=%s scope=%s atoms_linked=%s",
        swap.id,
        wallet_from_id,
        wallet_to_id,
        scope_from,
        linked,
    )
    return WalletLedgerSettleResult(
        applied=True,
        wallet_from_id=wallet_from_id,
        wallet_to_id=wallet_to_id,
    )


def settle_trade(
    db: Session,
    swap: PersonWalletSwap,
    *,
    wallet_from_id: UUID | None = None,
    wallet_to_id: UUID | None = None,
    quantities_confirmed: dict[str, Any] | None = None,
) -> WalletLedgerSettleResult:
    """Public entry — uses explicit IDs or reads from swap audit."""
    if wallet_from_id and wallet_to_id:
        from services.lifi.swap_repository import PersonWalletSwapRepository

        repo = PersonWalletSwapRepository()
        repo.append_audit(
            swap,
            {
                "event": "trade_wallet_context",
                "wallet_from_id": str(wallet_from_id),
                "wallet_to_id": str(wallet_to_id),
                "correlation_id": str(swap.id),
            },
        )
    return settle_trade_wallets(db, swap)
