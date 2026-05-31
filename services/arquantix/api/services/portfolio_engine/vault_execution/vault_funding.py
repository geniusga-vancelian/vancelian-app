"""Funding comptable Vault — transfert self-trading → vault scope sans mouvement Privy.

Modèle Vancelian (Phase 3A) :
  direct_portfolio SPOT (trading_available)  -= amount
  direct_portfolio SPOT (vault_position)     += amount
  person_wallet_balances / Privy             = inchangé

Pattern aligné sur ``bundle_funding.py`` — Lombard, bundle wrapper et Cost Basis
non modifiés ici.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution.bundle_cost_basis import reference_cost_basis_eur
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

logger = logging.getLogger(__name__)

PORTFOLIO_TYPE_DIRECT = "direct_portfolio"
PORTFOLIO_TYPE_VAULT = "vault_portfolio"
POSITION_TYPE_SPOT = PositionType.SPOT
TOLERANCE = Decimal("0.000001")

VAULT_SCOPE = "vault_position"
TRADING_SCOPE = "trading_available"

AUDIT_ENTITY_TYPE = "onchain_vault_transactions"
ACTION_FUND = "vault.fund_from_self_trading"
ACTION_RELEASE = "vault.release_to_self_trading"


class VaultFundingError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def ensure_vault_portfolio(db: Session, client_id: UUID) -> Portfolio:
    """Return the client's vault portfolio, creating it if absent."""
    existing = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == PORTFOLIO_TYPE_VAULT,
            Portfolio.status == "active",
        )
        .first()
    )
    if existing is not None:
        return existing

    portfolio = Portfolio(
        client_id=client_id,
        portfolio_type=PORTFOLIO_TYPE_VAULT,
        name="Vault Holdings",
        base_currency="USD",
        status="active",
        metadata_={"auto_provisioned": True, "scope": VAULT_SCOPE},
    )
    db.add(portfolio)
    db.flush()
    logger.info("Auto-provisioned vault_portfolio %s for client %s", portfolio.id, client_id)
    return portfolio


def _atom_metadata(atom: PositionAtom | None) -> dict[str, Any]:
    if atom is None:
        return {}
    meta = atom.metadata_
    return meta if isinstance(meta, dict) else {}


def _is_vault_position_atom(atom: PositionAtom) -> bool:
    meta = _atom_metadata(atom)
    scope = str(meta.get("scope") or "").lower()
    role = str(meta.get("role") or "").lower()
    return scope == VAULT_SCOPE or role == VAULT_SCOPE


def _is_trading_available_atom(atom: PositionAtom) -> bool:
    return atom.position_type == POSITION_TYPE_SPOT.value and not _is_vault_position_atom(atom)


def _find_trading_available_atom(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
) -> PositionAtom | None:
    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT.value,
            PositionAtom.status == "open",
        )
        .all()
    )
    return next((atom for atom in atoms if _is_trading_available_atom(atom)), None)


def sum_vault_position_quantity(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    vault_pf = ensure_vault_portfolio(db, client_id)
    atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == vault_pf.id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT.value,
            PositionAtom.status == "open",
        )
        .first()
    )
    if atom is None:
        return Decimal("0")
    return Decimal(str(atom.quantity or 0))


def resolve_vault_position_available(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    return sum_vault_position_quantity(
        db,
        client_id=client_id,
        instrument_id=instrument_id,
    )


def resolve_trading_available_for_vault(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = _find_trading_available_atom(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
    )
    if atom is None:
        return Decimal("0")
    return Decimal(str(atom.quantity or 0))


def _asset_symbol_for_instrument(db: Session, instrument_id: UUID) -> str:
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.instruments.models import Instrument

    instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if instrument is None:
        return "USDC"
    asset = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
    return str(asset.symbol).upper() if asset else "USDC"


def _cost_basis_for_trading_debit(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
    quantity: Decimal,
) -> Decimal:
    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = _find_trading_available_atom(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
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


def _cost_basis_for_vault_debit(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
    quantity: Decimal,
) -> Decimal:
    vault_pf = ensure_vault_portfolio(db, client_id)
    atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == vault_pf.id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT.value,
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


def _apply_trading_available_delta(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    quantity_delta: Decimal,
    cost_basis_delta: Decimal,
) -> PositionAtom:
    from services.portfolio_engine.direct_overlay import sync_direct_atom

    if quantity_delta < 0:
        return sync_direct_atom(
            db,
            portfolio_id,
            instrument_id,
            quantity_delta,
            cost_basis_delta,
        )
    if quantity_delta > 0:
        return sync_direct_atom(
            db,
            portfolio_id,
            instrument_id,
            quantity_delta,
            cost_basis_delta,
        )
    raise VaultFundingError("vault.funding.zero_delta", "Delta trading nul")


def _credit_vault_position_atom(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    quantity: Decimal,
    cost_basis: Decimal,
    linked_reference_id: str,
    integration_mode: str | None = None,
    tx_hash: str | None = None,
) -> PositionAtom:
    existing = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT.value,
            PositionAtom.status == "open",
        )
        .first()
    )
    if existing is not None:
        existing.quantity = Decimal(str(existing.quantity)) + quantity
        existing.available_quantity = Decimal(str(existing.available_quantity)) + quantity
        existing.cost_basis = Decimal(str(existing.cost_basis or 0)) + cost_basis
        if existing.quantity > 0:
            existing.average_entry_price = existing.cost_basis / existing.quantity
        db.flush()
        return existing

    atom = PositionAtom(
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        position_type=POSITION_TYPE_SPOT.value,
        status="open",
        quantity=quantity,
        available_quantity=quantity,
        cost_basis=cost_basis,
        average_entry_price=(cost_basis / quantity) if quantity > 0 else Decimal("0"),
        metadata_={
            "scope": VAULT_SCOPE,
            "role": VAULT_SCOPE,
            "linked_reference_id": linked_reference_id,
            **({"integration_mode": integration_mode} if integration_mode else {}),
            **({"tx_hash": tx_hash} if tx_hash else {}),
        },
    )
    db.add(atom)
    db.flush()
    return atom


def _debit_vault_position_atom(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
    quantity: Decimal,
    cost_basis: Decimal,
) -> PositionAtom:
    vault = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT.value,
            PositionAtom.status == "open",
        )
        .first()
    )
    if vault is None:
        raise VaultFundingError(
            "vault.release.vault_atom_missing",
            "Aucun atom vault_position pour ce release",
        )
    vault.quantity = Decimal(str(vault.quantity)) - quantity
    vault.available_quantity = Decimal(str(vault.available_quantity)) - quantity
    vault.cost_basis = Decimal(str(vault.cost_basis or 0)) - cost_basis
    if vault.quantity < 0:
        vault.quantity = Decimal("0")
        vault.available_quantity = Decimal("0")
    db.flush()
    return vault


def _vault_scope_movement_exists(
    db: Session,
    *,
    linked_reference_id: str,
    action: str,
) -> bool:
    from services.portfolio_engine.hardening.audit_models import AuditEvent

    return (
        db.query(AuditEvent.id)
        .filter(
            AuditEvent.entity_type == AUDIT_ENTITY_TYPE,
            AuditEvent.entity_id == linked_reference_id,
            AuditEvent.action == action,
        )
        .first()
        is not None
    )


def fund_vault_from_self_trading(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    asset: str,
    instrument_id: UUID,
    amount: Decimal,
    linked_reference_id: str,
    integration_mode: str | None = None,
    tx_hash: str | None = None,
) -> dict[str, Any]:
    """Phase 3A : trading_available − / vault_position +, Privy inchangé."""
    del person_id  # réservé hooks custody futurs (Phase 3A+)

    if amount <= 0:
        raise VaultFundingError("vault.funding.invalid_amount", "Montant de dépôt vault invalide")

    if _vault_scope_movement_exists(
        db,
        linked_reference_id=linked_reference_id,
        action=ACTION_FUND,
    ):
        logger.info(
            "vault_funding.idempotent_skip fund linked_reference_id=%s",
            linked_reference_id,
        )
        return {
            "action": "fund_vault_from_self_trading",
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "skipped": True,
            "reason": "already_applied",
            "privy_ledger_touched": False,
        }

    available = resolve_trading_available_for_vault(
        db,
        client_id=client_id,
        instrument_id=instrument_id,
    )
    if available + TOLERANCE < amount:
        raise VaultFundingError(
            "vault.funding.insufficient_trading_available",
            f"Solde trading_available {asset} insuffisant ({available} < {amount})",
        )

    cost_basis = _cost_basis_for_trading_debit(
        db,
        client_id=client_id,
        instrument_id=instrument_id,
        quantity=amount,
    )
    direct_pf = ensure_direct_portfolio(db, client_id)
    vault_pf = ensure_vault_portfolio(db, client_id)
    _apply_trading_available_delta(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
        quantity_delta=-amount,
        cost_basis_delta=-cost_basis,
    )
    vault_atom = _credit_vault_position_atom(
        db,
        portfolio_id=vault_pf.id,
        instrument_id=instrument_id,
        quantity=amount,
        cost_basis=cost_basis,
        linked_reference_id=linked_reference_id,
        integration_mode=integration_mode,
        tx_hash=tx_hash,
    )

    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type=AUDIT_ENTITY_TYPE,
        entity_id=linked_reference_id,
        action=ACTION_FUND,
        actor_id=f"vault-funding:{linked_reference_id}",
        metadata={
            "client_id": str(client_id),
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "cost_basis_eur": float(cost_basis),
            "vault_atom_id": str(vault_atom.id),
            "integration_mode": integration_mode,
            "tx_hash": tx_hash,
            "source_scope": TRADING_SCOPE,
            "destination_scope": VAULT_SCOPE,
        },
    )

    logger.info(
        "vault_funding.funded linked_reference_id=%s client=%s amount=%s %s cost_basis=%s",
        linked_reference_id,
        client_id,
        amount,
        asset,
        cost_basis,
    )
    return {
        "action": "fund_vault_from_self_trading",
        "linked_reference_id": linked_reference_id,
        "entry_asset": asset.upper(),
        "amount": float(amount),
        "cost_basis_eur": float(cost_basis),
        "vault_atom_id": str(vault_atom.id),
        "skipped": False,
        "privy_ledger_touched": False,
    }


def release_vault_to_self_trading(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    asset: str,
    instrument_id: UUID,
    amount: Decimal,
    linked_reference_id: str,
    integration_mode: str | None = None,
    tx_hash: str | None = None,
) -> dict[str, Any]:
    """Phase 3A : vault_position − / trading_available +, Privy inchangé."""
    del person_id

    if amount <= 0:
        raise VaultFundingError("vault.release.invalid_amount", "Montant de retrait vault invalide")

    if _vault_scope_movement_exists(
        db,
        linked_reference_id=linked_reference_id,
        action=ACTION_RELEASE,
    ):
        logger.info(
            "vault_funding.idempotent_skip release linked_reference_id=%s",
            linked_reference_id,
        )
        return {
            "action": "release_vault_to_self_trading",
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "skipped": True,
            "reason": "already_applied",
            "privy_ledger_touched": False,
        }

    available = resolve_vault_position_available(
        db,
        client_id=client_id,
        instrument_id=instrument_id,
    )
    if available + TOLERANCE < amount:
        raise VaultFundingError(
            "vault.release.insufficient_vault_position",
            f"Solde vault_position {asset} insuffisant ({available} < {amount})",
        )

    cost_basis = _cost_basis_for_vault_debit(
        db,
        client_id=client_id,
        instrument_id=instrument_id,
        quantity=amount,
    )
    direct_pf = ensure_direct_portfolio(db, client_id)
    vault_pf = ensure_vault_portfolio(db, client_id)
    _debit_vault_position_atom(
        db,
        portfolio_id=vault_pf.id,
        instrument_id=instrument_id,
        quantity=amount,
        cost_basis=cost_basis,
    )
    trading_atom = _apply_trading_available_delta(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
        quantity_delta=amount,
        cost_basis_delta=cost_basis,
    )

    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type=AUDIT_ENTITY_TYPE,
        entity_id=linked_reference_id,
        action=ACTION_RELEASE,
        actor_id=f"vault-funding:{linked_reference_id}",
        metadata={
            "client_id": str(client_id),
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "cost_basis_eur": float(cost_basis),
            "trading_atom_id": str(trading_atom.id),
            "integration_mode": integration_mode,
            "tx_hash": tx_hash,
            "source_scope": VAULT_SCOPE,
            "destination_scope": TRADING_SCOPE,
        },
    )

    logger.info(
        "vault_funding.released linked_reference_id=%s client=%s amount=%s %s cost_basis=%s",
        linked_reference_id,
        client_id,
        amount,
        asset,
        cost_basis,
    )
    return {
        "action": "release_vault_to_self_trading",
        "linked_reference_id": linked_reference_id,
        "entry_asset": asset.upper(),
        "amount": float(amount),
        "cost_basis_eur": float(cost_basis),
        "trading_atom_id": str(trading_atom.id),
        "skipped": False,
        "privy_ledger_touched": False,
    }
