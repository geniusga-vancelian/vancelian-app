"""Virtual wallet resolution — one WalletContainer per (portfolio × instrument × type)."""
from __future__ import annotations

import logging
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

from .enums import WalletType
from .models import WalletContainer
from .repository import WalletContainerRepository

logger = logging.getLogger(__name__)

PORTFOLIO_TYPE_DIRECT = "direct_portfolio"
PORTFOLIO_TYPE_BUNDLE = "bundle_portfolio"


class VirtualWalletNotFoundError(Exception):
    def __init__(self, *, portfolio_id: UUID, instrument_id: UUID, wallet_type: str):
        self.portfolio_id = portfolio_id
        self.instrument_id = instrument_id
        self.wallet_type = wallet_type
        super().__init__(
            f"virtual_wallet_not_found portfolio={portfolio_id} "
            f"instrument={instrument_id} type={wallet_type}",
        )


def find_wallet(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    wallet_type: str,
) -> Optional[WalletContainer]:
    return (
        db.query(WalletContainer)
        .filter(
            WalletContainer.portfolio_id == portfolio_id,
            WalletContainer.instrument_id == instrument_id,
            WalletContainer.wallet_type == wallet_type,
            WalletContainer.status == "active",
        )
        .first()
    )


def resolve_wallet(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    wallet_type: str,
    client_id: UUID | None = None,
    create_if_missing: bool = True,
) -> WalletContainer:
    existing = find_wallet(
        db,
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        wallet_type=wallet_type,
    )
    if existing is not None:
        return existing
    if not create_if_missing:
        raise VirtualWalletNotFoundError(
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            wallet_type=wallet_type,
        )
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    resolved_client = client_id or (portfolio.client_id if portfolio else None)
    wallet = WalletContainerRepository.create(
        db,
        data={
            "client_id": resolved_client,
            "portfolio_id": portfolio_id,
            "wallet_type": wallet_type,
            "instrument_id": instrument_id,
            "custody_provider": "virtual",
            "status": "active",
            "metadata_": {"auto_provisioned": True},
        },
    )
    logger.info(
        "virtual_wallet_provisioned portfolio=%s instrument=%s type=%s id=%s",
        portfolio_id,
        instrument_id,
        wallet_type,
        wallet.id,
    )
    return wallet


def resolve_spot_wallet(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    client_id: UUID | None = None,
) -> WalletContainer:
    return resolve_wallet(
        db,
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        wallet_type=WalletType.SPOT_WALLET.value,
        client_id=client_id,
    )


def resolve_cash_wallet(
    db: Session,
    *,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
    client_id: UUID | None = None,
) -> WalletContainer:
    return resolve_wallet(
        db,
        portfolio_id=portfolio_id,
        instrument_id=entry_instrument_id,
        wallet_type=WalletType.CASH_WALLET.value,
        client_id=client_id,
    )


def ensure_portfolio_wallets(
    db: Session,
    *,
    portfolio_id: UUID,
    client_id: UUID,
    spot_instrument_ids: Iterable[UUID],
    entry_instrument_id: UUID | None = None,
) -> dict[str, list[UUID]]:
    """Bootstrap virtual wallets for a portfolio. Idempotent."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio is None:
        raise ValueError(f"portfolio_not_found:{portfolio_id}")

    created_spot: list[UUID] = []
    for instrument_id in spot_instrument_ids:
        wallet = resolve_spot_wallet(
            db,
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            client_id=client_id,
        )
        created_spot.append(wallet.id)

    cash_wallet_ids: list[UUID] = []
    is_bundle = str(portfolio.portfolio_type or "") == PORTFOLIO_TYPE_BUNDLE
    if is_bundle and entry_instrument_id is not None:
        cash = resolve_cash_wallet(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=entry_instrument_id,
            client_id=client_id,
        )
        cash_wallet_ids.append(cash.id)

    return {"spot_wallet_ids": created_spot, "cash_wallet_ids": cash_wallet_ids}


def resolve_trade_wallets_for_leg(
    db: Session,
    *,
    portfolio_id: UUID,
    client_id: UUID,
    leg_action: str,
    from_instrument_id: UUID,
    to_instrument_id: UUID,
    entry_instrument_id: UUID,
) -> tuple[UUID, UUID]:
    """Map rebalance/allocation leg action → (wallet_from_id, wallet_to_id)."""
    if leg_action in ("rebalance_buy", "allocation"):
        wallet_from = resolve_cash_wallet(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=from_instrument_id,
            client_id=client_id,
        )
        wallet_to = resolve_spot_wallet(
            db,
            portfolio_id=portfolio_id,
            instrument_id=to_instrument_id,
            client_id=client_id,
        )
        return wallet_from.id, wallet_to.id

    if leg_action == "rebalance_sell":
        wallet_from = resolve_spot_wallet(
            db,
            portfolio_id=portfolio_id,
            instrument_id=from_instrument_id,
            client_id=client_id,
        )
        wallet_to = resolve_cash_wallet(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=to_instrument_id,
            client_id=client_id,
        )
        return wallet_from.id, wallet_to.id

    if leg_action == "withdraw_sell":
        wallet_from = resolve_spot_wallet(
            db,
            portfolio_id=portfolio_id,
            instrument_id=from_instrument_id,
            client_id=client_id,
        )
        wallet_to = resolve_cash_wallet(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=to_instrument_id,
            client_id=client_id,
        )
        return wallet_from.id, wallet_to.id

    wallet_from = resolve_spot_wallet(
        db,
        portfolio_id=portfolio_id,
        instrument_id=from_instrument_id,
        client_id=client_id,
    )
    wallet_to = resolve_spot_wallet(
        db,
        portfolio_id=portfolio_id,
        instrument_id=to_instrument_id,
        client_id=client_id,
    )
    return wallet_from.id, wallet_to.id


def backfill_position_atom_wallet_ids(
    db: Session,
    *,
    portfolio_id: UUID,
    client_id: UUID | None = None,
) -> int:
    """Link open PositionAtoms to their virtual wallets. Returns count updated."""
    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.status == "open",
        )
        .all()
    )
    updated = 0
    for atom in atoms:
        if atom.wallet_id is not None:
            continue
        wallet_type = (
            WalletType.CASH_WALLET.value
            if atom.position_type == PositionType.CASH
            else WalletType.SPOT_WALLET.value
        )
        wallet = resolve_wallet(
            db,
            portfolio_id=portfolio_id,
            instrument_id=atom.instrument_id,
            wallet_type=wallet_type,
            client_id=client_id,
        )
        atom.wallet_id = wallet.id
        updated += 1
    if updated:
        db.flush()
    return updated


def portfolio_scope_from_wallet(db: Session, wallet_id: UUID) -> tuple[str, UUID | None]:
    """Derive ADR 006 portfolio_scope from a virtual wallet."""
    wallet = WalletContainerRepository.get_by_id(db, wallet_id)
    if wallet is None or wallet.portfolio_id is None:
        return "direct", None
    portfolio = db.query(Portfolio).filter(Portfolio.id == wallet.portfolio_id).first()
    if portfolio is None:
        return "direct", None
    if str(portfolio.portfolio_type or "") == PORTFOLIO_TYPE_BUNDLE:
        return "bundle", portfolio.id
    return "direct", portfolio.id
