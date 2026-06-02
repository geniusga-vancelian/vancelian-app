"""Funding comptable Lombard — lock collateral + borrow USDC (Phase 3B).

Contrainte schéma : un seul atom open par (portfolio_id, instrument_id)
(``ix_pe_position_atoms_unique_open``). Le lock collateral utilise donc
``available_quantity`` / ``locked_quantity`` sur l'atom SPOT existant ;
la dette USDC est portée dans ``metadata.lombard_liability_usdc`` sur l'atom
USDC SPOT (pas d'atom BORROWING séparé sur le même instrument).

Privy / person_wallet_balances inchangés — reclassement de scope PE uniquement.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.direct_overlay import ensure_direct_portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

logger = logging.getLogger(__name__)

POSITION_TYPE_SPOT = PositionType.SPOT
TOLERANCE = Decimal("0.000001")

TRADING_SCOPE = "trading_available"
LOCKED_SCOPE = "trading_locked_collateral"
LIABILITY_SCOPE = "liability"

AUDIT_ENTITY_TYPE = "onchain_vault_transactions"
ACTION_LOCK = "lombard.lock_collateral"
ACTION_BORROW = "lombard.open_borrow"

LOMBARD_LIABILITY_METADATA_KEY = "lombard_liability_usdc"


class LombardFundingError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def lombard_liability_usdc_from_metadata(meta: dict[str, Any] | None) -> Decimal:
    if not isinstance(meta, dict):
        return Decimal("0")
    raw = meta.get(LOMBARD_LIABILITY_METADATA_KEY)
    if raw is None:
        nested = meta.get("lombard")
        if isinstance(nested, dict):
            raw = nested.get("liability_usdc")
    if raw is None:
        return Decimal("0")
    try:
        return max(Decimal("0"), Decimal(str(raw)))
    except Exception:
        return Decimal("0")


def _atom_metadata(atom: PositionAtom | None) -> dict[str, Any]:
    if atom is None:
        return {}
    meta = atom.metadata_
    return meta if isinstance(meta, dict) else {}


def _find_direct_spot_atom(
    db: Session,
    *,
    portfolio_id: UUID,
    instrument_id: UUID,
) -> PositionAtom | None:
    return (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT.value,
            PositionAtom.status == "open",
        )
        .first()
    )


def _lombard_scope_movement_exists(
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


def resolve_trading_available_for_lombard(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = _find_direct_spot_atom(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
    )
    if atom is None:
        return Decimal("0")
    return Decimal(str(atom.available_quantity or 0))


def resolve_trading_locked_collateral_for_lombard(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = _find_direct_spot_atom(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
    )
    if atom is None:
        return Decimal("0")
    return Decimal(str(atom.locked_quantity or 0))


def resolve_lombard_liability_usdc(
    db: Session,
    *,
    client_id: UUID,
    instrument_id: UUID,
) -> Decimal:
    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = _find_direct_spot_atom(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
    )
    if atom is None:
        return Decimal("0")
    return lombard_liability_usdc_from_metadata(_atom_metadata(atom))


def lock_lombard_collateral_from_trading(
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
    group_key: str | None = None,
) -> dict[str, Any]:
    """Reclasse collateral : trading_available − / trading_locked_collateral + (même atom SPOT)."""
    del person_id

    if amount <= 0:
        raise LombardFundingError(
            "lombard.lock.invalid_amount",
            "Montant de lock collateral Lombard invalide",
        )

    if _lombard_scope_movement_exists(
        db,
        linked_reference_id=linked_reference_id,
        action=ACTION_LOCK,
    ):
        logger.info(
            "lombard_funding.idempotent_skip lock linked_reference_id=%s",
            linked_reference_id,
        )
        return {
            "action": "lock_lombard_collateral_from_trading",
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "skipped": True,
            "reason": "already_applied",
        }

    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = _find_direct_spot_atom(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
    )
    if atom is None:
        raise LombardFundingError(
            "lombard.lock.collateral_atom_missing",
            f"Aucun atom trading_available {asset} pour le lock Lombard",
        )

    available = Decimal(str(atom.available_quantity or 0))
    if available + TOLERANCE < amount:
        raise LombardFundingError(
            "lombard.lock.insufficient_trading_available",
            f"Solde trading_available {asset} insuffisant ({available} < {amount})",
        )

    locked = Decimal(str(atom.locked_quantity or 0))
    atom.available_quantity = available - amount
    atom.locked_quantity = locked + amount
    meta = dict(_atom_metadata(atom))
    meta.setdefault("lombard_locks", [])
    if isinstance(meta["lombard_locks"], list):
        meta["lombard_locks"].append(
            {
                "linked_reference_id": linked_reference_id,
                "amount": str(amount),
                "group_key": group_key,
            }
        )
    atom.metadata_ = meta
    db.flush()

    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type=AUDIT_ENTITY_TYPE,
        entity_id=linked_reference_id,
        action=ACTION_LOCK,
        actor_id=f"lombard-funding:{linked_reference_id}",
        metadata={
            "client_id": str(client_id),
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "spot_atom_id": str(atom.id),
            "integration_mode": integration_mode,
            "tx_hash": tx_hash,
            "group_key": group_key,
            "source_scope": TRADING_SCOPE,
            "destination_scope": LOCKED_SCOPE,
            "representation": "spot_available_to_locked_quantity",
        },
    )

    logger.info(
        "lombard_funding.locked linked_reference_id=%s client=%s amount=%s %s",
        linked_reference_id,
        client_id,
        amount,
        asset,
    )
    return {
        "action": "lock_lombard_collateral_from_trading",
        "linked_reference_id": linked_reference_id,
        "entry_asset": asset.upper(),
        "amount": float(amount),
        "spot_atom_id": str(atom.id),
        "skipped": False,
    }


def credit_lombard_borrow_to_trading(
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
    group_key: str | None = None,
) -> dict[str, Any]:
    """Crédite emprunt USDC : liability + (metadata) et trading_available + (quantity/available)."""
    del person_id

    if amount <= 0:
        raise LombardFundingError(
            "lombard.borrow.invalid_amount",
            "Montant d'emprunt Lombard invalide",
        )

    if _lombard_scope_movement_exists(
        db,
        linked_reference_id=linked_reference_id,
        action=ACTION_BORROW,
    ):
        logger.info(
            "lombard_funding.idempotent_skip borrow linked_reference_id=%s",
            linked_reference_id,
        )
        return {
            "action": "credit_lombard_borrow_to_trading",
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "skipped": True,
            "reason": "already_applied",
        }

    direct_pf = ensure_direct_portfolio(db, client_id)
    atom = _find_direct_spot_atom(
        db,
        portfolio_id=direct_pf.id,
        instrument_id=instrument_id,
    )
    if atom is None:
        atom = PositionAtom(
            portfolio_id=direct_pf.id,
            instrument_id=instrument_id,
            position_type=POSITION_TYPE_SPOT.value,
            status="open",
            quantity=amount,
            available_quantity=amount,
            locked_quantity=Decimal("0"),
            cost_basis=Decimal("0"),
            average_entry_price=Decimal("0"),
            metadata_={"scope": "direct"},
        )
        db.add(atom)
        db.flush()
    else:
        atom.quantity = Decimal(str(atom.quantity or 0)) + amount
        atom.available_quantity = Decimal(str(atom.available_quantity or 0)) + amount
        db.flush()

    meta = dict(_atom_metadata(atom))
    prior_liability = lombard_liability_usdc_from_metadata(meta)
    meta[LOMBARD_LIABILITY_METADATA_KEY] = str(prior_liability + amount)
    meta.setdefault("lombard_borrows", [])
    if isinstance(meta["lombard_borrows"], list):
        meta["lombard_borrows"].append(
            {
                "linked_reference_id": linked_reference_id,
                "amount": str(amount),
                "group_key": group_key,
            }
        )
    atom.metadata_ = meta
    db.flush()

    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type=AUDIT_ENTITY_TYPE,
        entity_id=linked_reference_id,
        action=ACTION_BORROW,
        actor_id=f"lombard-funding:{linked_reference_id}",
        metadata={
            "client_id": str(client_id),
            "linked_reference_id": linked_reference_id,
            "entry_asset": asset.upper(),
            "amount": float(amount),
            "spot_atom_id": str(atom.id),
            "integration_mode": integration_mode,
            "tx_hash": tx_hash,
            "group_key": group_key,
            "source_scope": LIABILITY_SCOPE,
            "destination_scope": TRADING_SCOPE,
            "representation": "spot_metadata_liability_and_available_credit",
            "liability_usdc_total": str(prior_liability + amount),
        },
    )

    logger.info(
        "lombard_funding.borrowed linked_reference_id=%s client=%s amount=%s %s",
        linked_reference_id,
        client_id,
        amount,
        asset,
    )
    return {
        "action": "credit_lombard_borrow_to_trading",
        "linked_reference_id": linked_reference_id,
        "entry_asset": asset.upper(),
        "amount": float(amount),
        "spot_atom_id": str(atom.id),
        "skipped": False,
    }


def open_lombard_loan(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    collateral_asset: str,
    collateral_instrument_id: UUID,
    collateral_amount: Decimal,
    borrow_amount: Decimal,
    linked_reference_id: str,
    integration_mode: str | None = None,
    tx_hash: str | None = None,
    group_key: str | None = None,
) -> dict[str, Any]:
    """Lock collateral puis crédit borrow — transaction DB atomique (fail closed)."""
    lock_result: dict[str, Any] | None = None
    borrow_result: dict[str, Any] | None = None

    if collateral_amount > 0:
        lock_result = lock_lombard_collateral_from_trading(
            db,
            client_id=client_id,
            person_id=person_id,
            asset=collateral_asset,
            instrument_id=collateral_instrument_id,
            amount=collateral_amount,
            linked_reference_id=linked_reference_id,
            integration_mode=integration_mode,
            tx_hash=tx_hash,
            group_key=group_key,
        )

    if borrow_amount > 0:
        from services.portfolio_engine.direct_overlay import _resolve_or_create_instrument

        usdc = _resolve_or_create_instrument(db, "USDC")
        borrow_result = credit_lombard_borrow_to_trading(
            db,
            client_id=client_id,
            person_id=person_id,
            asset="USDC",
            instrument_id=usdc.id,
            amount=borrow_amount,
            linked_reference_id=linked_reference_id,
            integration_mode=integration_mode,
            tx_hash=tx_hash,
            group_key=group_key,
        )

    return {
        "action": "open_lombard_loan",
        "linked_reference_id": linked_reference_id,
        "lock": lock_result,
        "borrow": borrow_result,
    }
