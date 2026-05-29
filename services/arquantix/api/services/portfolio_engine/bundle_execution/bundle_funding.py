"""Funding comptable bundle — transfert self-trading → cash leg sans mouvement Privy.

Modèle Vancelian :
  direct_portfolio(entry_asset) -= amount
  bundle_cash_leg(entry_asset)  += amount
  ledger Privy                  = inchangé
"""
from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution.bundle_cost_basis import reference_cost_basis_eur
from services.portfolio_engine.direct_overlay import (
    ensure_direct_portfolio,
    sync_direct_atom,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

logger = logging.getLogger(__name__)

PORTFOLIO_TYPE_BUNDLE = "bundle_portfolio"
PORTFOLIO_TYPE_DIRECT = "direct_portfolio"
TOLERANCE = Decimal("0.000001")


class BundleFundingError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def sum_bundle_cash_leg_quantity(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    """Somme des cash legs ouverts pour un instrument d'entrée bundle."""
    bundle_portfolio_ids = [
        row[0]
        for row in db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == PORTFOLIO_TYPE_BUNDLE,
            Portfolio.status == "active",
        )
        .all()
    ]
    if not bundle_portfolio_ids:
        return Decimal("0")

    total = (
        db.query(sa_func.coalesce(sa_func.sum(PositionAtom.quantity), 0))
        .filter(
            PositionAtom.portfolio_id.in_(bundle_portfolio_ids),
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == PositionType.CASH,
            PositionAtom.status == "open",
        )
        .scalar()
    )
    return Decimal(str(total or 0))


def _direct_spot_quantity(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == PositionType.SPOT,
            PositionAtom.status == "open",
        )
        .first()
    )
    if atom is None:
        return Decimal("0")
    return Decimal(str(atom.quantity or 0))


def _privy_balance_for_asset(db: Session, *, person_id: UUID | None, asset: str) -> Decimal:
    if person_id is None:
        return Decimal("0")
    try:
        from services.privy_wallet.repository import PersonWalletBalanceRepository
    except ImportError:
        return Decimal("0")

    total = Decimal("0")
    asset_u = asset.strip().upper()
    for row in PersonWalletBalanceRepository.list_for_person(db, person_id):
        if str(row.asset or "").upper() != asset_u:
            continue
        total += Decimal(str(row.balance or 0))
    return total


def _cost_basis_for_direct_debit(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
    quantity: Decimal,
) -> Decimal:
    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == PositionType.SPOT,
            PositionAtom.status == "open",
        )
        .first()
    )
    if atom is None:
        entry_asset = _asset_symbol_for_instrument(db, instrument_id)
        return reference_cost_basis_eur(db, entry_asset, quantity)

    atom_qty = Decimal(str(atom.quantity or 0))
    atom_cost = Decimal(str(atom.cost_basis or 0))
    if atom_qty <= 0 or atom_cost <= 0:
        entry_asset = _asset_symbol_for_instrument(db, instrument_id)
        return reference_cost_basis_eur(db, entry_asset, quantity)

    ratio = min(Decimal("1"), quantity / atom_qty)
    return (atom_cost * ratio).quantize(Decimal("0.01"))


def _asset_symbol_for_instrument(db: Session, instrument_id: UUID) -> str:
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.instruments.models import Instrument

    instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if instrument is None:
        return "USDC"
    asset = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
    return str(asset.symbol).upper() if asset else "USDC"


def sync_self_trading_atom_from_custody(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    entry_asset: str,
    entry_instrument_id: UUID,
) -> Decimal:
    """Aligne l'atom direct sur custody Privy − cash legs bundle (bootstrap si besoin).

    Ne réduit jamais l'atom direct uniquement parce que Privy est vide (clients Exchange-only).
    """
    current_direct = _direct_spot_quantity(
        db, client_id=client_id, instrument_id=entry_instrument_id,
    )
    if person_id is None:
        return current_direct

    privy_qty = _privy_balance_for_asset(db, person_id=person_id, asset=entry_asset)
    if privy_qty <= TOLERANCE:
        return current_direct

    bundle_cash = sum_bundle_cash_leg_quantity(
        db, client_id=client_id, instrument_id=entry_instrument_id,
    )
    expected_direct = max(Decimal("0"), privy_qty - bundle_cash)
    delta = expected_direct - current_direct
    if delta <= TOLERANCE:
        return max(current_direct, expected_direct)

    cost_basis = reference_cost_basis_eur(db, entry_asset, delta)
    direct_pf = ensure_direct_portfolio(db, client_id)
    sync_direct_atom(
        db,
        direct_pf.id,
        entry_instrument_id,
        delta,
        cost_basis,
    )
    logger.info(
        "bundle_funding.sync_self_trading client=%s asset=%s delta=%s privy=%s bundle_cash=%s",
        client_id,
        entry_asset,
        delta,
        privy_qty,
        bundle_cash,
    )
    return expected_direct


def _bootstrap_direct_from_crypto_positions(
    db: Session,
    *,
    client_id: UUID,
    entry_asset: str,
    entry_instrument_id: UUID,
) -> Decimal:
    """Bootstrap l'atom direct depuis ``crypto_positions`` (achats Exchange non bundle)."""
    from services.exchange.models import CryptoPosition

    pos = (
        db.query(CryptoPosition)
        .filter(
            CryptoPosition.client_id == client_id,
            CryptoPosition.asset == entry_asset.upper(),
        )
        .first()
    )
    if pos is None:
        return _direct_spot_quantity(
            db, client_id=client_id, instrument_id=entry_instrument_id,
        )

    platform_total = Decimal(str(pos.balance or 0))
    if platform_total <= TOLERANCE:
        return _direct_spot_quantity(
            db, client_id=client_id, instrument_id=entry_instrument_id,
        )

    bundle_cash = sum_bundle_cash_leg_quantity(
        db, client_id=client_id, instrument_id=entry_instrument_id,
    )
    expected_direct = max(Decimal("0"), platform_total - bundle_cash)
    current_direct = _direct_spot_quantity(
        db, client_id=client_id, instrument_id=entry_instrument_id,
    )
    delta = expected_direct - current_direct
    if delta <= TOLERANCE:
        return current_direct

    cost_basis = reference_cost_basis_eur(db, entry_asset, delta)
    direct_pf = ensure_direct_portfolio(db, client_id)
    sync_direct_atom(
        db,
        direct_pf.id,
        entry_instrument_id,
        delta,
        cost_basis,
    )
    logger.info(
        "bundle_funding.bootstrap_from_crypto_positions client=%s asset=%s delta=%s platform=%s bundle_cash=%s",
        client_id,
        entry_asset,
        delta,
        platform_total,
        bundle_cash,
    )
    return expected_direct


def resolve_self_trading_available(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    entry_asset: str,
    entry_instrument_id: UUID,
) -> Decimal:
    """Solde self-trading disponible pour alimenter un bundle (sans swap)."""
    sync_self_trading_atom_from_custody(
        db,
        client_id=client_id,
        person_id=person_id,
        entry_asset=entry_asset,
        entry_instrument_id=entry_instrument_id,
    )
    _bootstrap_direct_from_crypto_positions(
        db,
        client_id=client_id,
        entry_asset=entry_asset,
        entry_instrument_id=entry_instrument_id,
    )
    return _direct_spot_quantity(
        db, client_id=client_id, instrument_id=entry_instrument_id,
    )


def fund_bundle_cash_leg_from_self_trading(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    portfolio_id: UUID,
    entry_asset: str,
    entry_instrument_id: UUID,
    amount: Decimal,
    batch_id: str,
) -> dict:
    """Étape 1 Vancelian : self-trading → cash leg bundle, Privy inchangé."""
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    if amount <= 0:
        raise BundleFundingError("bundle.funding.invalid_amount", "Montant de funding invalide")

    available = resolve_self_trading_available(
        db,
        client_id=client_id,
        person_id=person_id,
        entry_asset=entry_asset,
        entry_instrument_id=entry_instrument_id,
    )
    if available + TOLERANCE < amount:
        raise BundleFundingError(
            "bundle.funding.insufficient_self_trading",
            f"Solde self-trading {entry_asset} insuffisant ({available} < {amount})",
        )

    cost_basis = _cost_basis_for_direct_debit(
        db,
        client_id=client_id,
        instrument_id=entry_instrument_id,
        quantity=amount,
    )
    direct_pf = ensure_direct_portfolio(db, client_id)
    sync_direct_atom(
        db,
        direct_pf.id,
        entry_instrument_id,
        -amount,
        -cost_basis,
    )
    cash_atom = BundleOrchestrator._credit_cash_leg(
        db,
        portfolio_id,
        entry_instrument_id,
        amount,
        cost_basis,
    )

    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    portfolio_name = portfolio.name if portfolio is not None else "Bundle"
    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type="portfolio",
        entity_id=str(portfolio_id),
        action="bundle.fund_cash_leg",
        actor_id=f"bundle-funding:{batch_id}",
        metadata={
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "portfolio_name": portfolio_name,
            "batch_id": batch_id,
            "entry_asset": entry_asset.upper(),
            "amount": float(amount),
            "cost_basis_eur": float(cost_basis),
            "cash_leg_atom_id": str(cash_atom.id),
        },
    )

    logger.info(
        "bundle_funding.funded batch=%s client=%s portfolio=%s amount=%s %s cost_basis=%s",
        batch_id,
        client_id,
        portfolio_id,
        amount,
        entry_asset,
        cost_basis,
    )
    from services.portfolio_engine.bundle_ledger.service import record_bundle_deposit

    record_bundle_deposit(
        db,
        person_id=person_id,
        client_id=client_id,
        bundle_portfolio_id=portfolio_id,
        entry_asset=entry_asset,
        entry_instrument_id=entry_instrument_id,
        amount=amount,
        batch_id=batch_id,
        cost_basis_eur=cost_basis,
        cash_leg_atom_id=str(cash_atom.id),
    )
    return {
        "action": "fund_cash_leg_from_self_trading",
        "batch_id": batch_id,
        "entry_asset": entry_asset.upper(),
        "amount": float(amount),
        "cost_basis_eur": float(cost_basis),
        "cash_leg_atom_id": str(cash_atom.id),
        "privy_ledger_touched": False,
    }


def _cost_basis_for_cash_leg_debit(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    quantity: Decimal,
) -> Decimal:
    cash = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == PositionType.CASH,
            PositionAtom.status == "open",
        )
        .first()
    )
    if cash is None:
        entry_asset = _asset_symbol_for_instrument(db, instrument_id)
        return reference_cost_basis_eur(db, entry_asset, quantity)

    cash_qty = Decimal(str(cash.quantity or 0))
    cash_cost = Decimal(str(cash.cost_basis or 0))
    if cash_qty <= 0 or cash_cost <= 0:
        entry_asset = _asset_symbol_for_instrument(db, instrument_id)
        return reference_cost_basis_eur(db, entry_asset, quantity)

    ratio = min(Decimal("1"), quantity / cash_qty)
    return (cash_cost * ratio).quantize(Decimal("0.01"))


def resolve_bundle_cash_leg_available(
    db: Session,
    *,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
) -> Decimal:
    cash = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == entry_instrument_id,
            PositionAtom.position_type == PositionType.CASH,
            PositionAtom.status == "open",
        )
        .first()
    )
    if cash is None:
        return Decimal("0")
    return Decimal(str(cash.quantity or 0))


def release_bundle_cash_leg_to_self_trading(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    portfolio_id: UUID,
    entry_asset: str,
    entry_instrument_id: UUID,
    amount: Decimal,
    batch_id: str,
) -> dict:
    """Étape finale retrait : cash leg bundle → self-trading, Privy inchangé."""
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    if amount <= 0:
        raise BundleFundingError("bundle.release.invalid_amount", "Montant de release invalide")

    available = resolve_bundle_cash_leg_available(
        db,
        portfolio_id=portfolio_id,
        entry_instrument_id=entry_instrument_id,
    )
    if available + TOLERANCE < amount:
        raise BundleFundingError(
            "bundle.release.insufficient_cash_leg",
            f"Cash leg {entry_asset} insuffisant ({available} < {amount})",
        )

    cost_basis = _cost_basis_for_cash_leg_debit(
        db,
        portfolio_id=portfolio_id,
        instrument_id=entry_instrument_id,
        quantity=amount,
    )
    BundleOrchestrator._debit_cash_leg(
        db,
        portfolio_id,
        entry_instrument_id,
        amount,
        cost_basis,
    )
    direct_pf = ensure_direct_portfolio(db, client_id)
    sync_direct_atom(
        db,
        direct_pf.id,
        entry_instrument_id,
        amount,
        cost_basis,
    )

    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    portfolio_name = portfolio.name if portfolio is not None else "Bundle"
    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type="portfolio",
        entity_id=str(portfolio_id),
        action="bundle.release_cash_leg",
        actor_id=f"bundle-funding:{batch_id}",
        metadata={
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "portfolio_name": portfolio_name,
            "batch_id": batch_id,
            "entry_asset": entry_asset.upper(),
            "amount": float(amount),
            "cost_basis_eur": float(cost_basis),
        },
    )

    logger.info(
        "bundle_funding.released batch=%s client=%s portfolio=%s amount=%s %s cost_basis=%s",
        batch_id,
        client_id,
        portfolio_id,
        amount,
        entry_asset,
        cost_basis,
    )
    from services.portfolio_engine.bundle_ledger.service import record_bundle_withdrawal

    record_bundle_withdrawal(
        db,
        person_id=person_id,
        client_id=client_id,
        bundle_portfolio_id=portfolio_id,
        entry_asset=entry_asset,
        entry_instrument_id=entry_instrument_id,
        amount=amount,
        batch_id=batch_id,
        cost_basis_eur=cost_basis,
    )
    return {
        "action": "release_cash_leg_to_self_trading",
        "batch_id": batch_id,
        "entry_asset": entry_asset.upper(),
        "amount": float(amount),
        "cost_basis_eur": float(cost_basis),
        "privy_ledger_touched": False,
    }
