"""Lending Valuation Layer — Phase 2A.5 + 2A.7.

Provides position-level and portfolio-level valuation for lending/borrowing,
using the same pricing source as spot (MarketDataLatestQuote via price_bridge).

INVARIANT: This module is READ-ONLY and ADDITIVE.
It does NOT modify _compute_atoms_value, crypto_positions, or any existing
valuation path. It creates a parallel view for wealth management.

Pricing rules (Phase 2A.7 — includes accrued interest):
  SPOT:      value =  quantity × spot_price
  LENDING:   value =  (quantity + accrued_income) × spot_price  (principal + interest claim)
  BORROWING: value = -(quantity + accrued_income) × spot_price  (principal + interest obligation)
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.valuation import get_fx_rate, _ZERO

logger = logging.getLogger(__name__)

_ROUND = Decimal("0.01")


def _get_atom_price_usdt(db: Session, instrument_id: UUID) -> Optional[Decimal]:
    """Get current USDT price for an instrument via the price bridge."""
    from services.portfolio_engine.instruments.price_bridge import get_instrument_price
    try:
        pi = get_instrument_price(db, instrument_id)
        if pi.get("price"):
            return Decimal(pi["price"])
    except Exception:
        pass
    return None


def _get_atom_asset_symbol(db: Session, instrument_id: UUID) -> Optional[str]:
    """Resolve asset symbol from instrument."""
    instr = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if instr is None:
        return None
    asset = db.query(Asset).filter(Asset.id == instr.asset_id).first()
    return asset.symbol if asset else None


# ── Position-level valuation ──────────────────────────────────────

def compute_position_market_value(
    db: Session,
    atom: PositionAtom,
    *,
    eurusdt_rate: Optional[Decimal] = None,
) -> dict:
    """Compute the market value of a single PositionAtom.

    Returns dict with:
      - asset, quantity, position_type
      - price_usdt, price_eur
      - market_value_eur (negative for borrowing)
      - loan_id (from metadata if present)
    """
    from services.market_data.fx import usdt_to_eur

    if eurusdt_rate is None:
        eurusdt_rate = get_fx_rate(db)

    quantity = Decimal(str(atom.quantity))
    accrued = Decimal(str(atom.accrued_income or 0))
    effective_quantity = quantity + accrued if atom.position_type in ("lending", "borrowing") else quantity

    price_usdt = _get_atom_price_usdt(db, atom.instrument_id)
    asset_symbol = _get_atom_asset_symbol(db, atom.instrument_id)

    if price_usdt is None:
        price_eur = _ZERO
        value_eur = _ZERO
        value_usdt = _ZERO
    else:
        price_eur = usdt_to_eur(price_usdt, eurusdt_rate)
        value_eur = (effective_quantity * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
        value_usdt = (effective_quantity * price_usdt).quantize(_ROUND, rounding=ROUND_HALF_UP)

    sign = Decimal("-1") if atom.position_type == "borrowing" else Decimal("1")

    meta = atom.metadata_ or {}

    return {
        "atom_id": str(atom.id),
        "asset": asset_symbol,
        "quantity": float(quantity),
        "accrued_interest": float(accrued),
        "effective_quantity": float(effective_quantity),
        "position_type": atom.position_type,
        "price_usdt": float(price_usdt) if price_usdt else None,
        "price_eur": float(price_eur),
        "market_value_eur": float(sign * value_eur),
        "market_value_usdt": float(sign * value_usdt),
        "loan_id": meta.get("loan_id"),
        "counterparty": meta.get("counterparty"),
        "status": atom.status,
        "opened_at": atom.opened_at.isoformat() if atom.opened_at else None,
        "closed_at": atom.closed_at.isoformat() if atom.closed_at else None,
    }


# ── Portfolio-level valuation (V2 — wealth view) ─────────────────

def compute_total_portfolio_value_v2(db: Session, client_id: UUID) -> dict:
    """Wealth view: spot + lending - borrowing.

    Spot source of truth: crypto_positions (same as get_portfolio_breakdown).
    Lending/borrowing: pe_position_atoms filtered by position_type.

    Returns:
      {
        "spot_value_eur": ...,
        "lending_value_eur": ...,
        "borrowing_value_eur": ...,  (positive number — the debt amount)
        "net_value_eur": ...,        (spot + lending - borrowing)
        "spot_count": ...,
        "lending_count": ...,
        "borrowing_count": ...,
        "lending_positions": [...],
        "borrowing_positions": [...],
      }
    """
    from services.market_data.fx import usdt_to_eur
    from services.portfolio_engine.valuation import get_crypto_value_eur
    from services.exchange.repository import CryptoPositionRepository

    eurusdt_rate = get_fx_rate(db)

    # Spot: from crypto_positions (single source of truth for spot balances)
    spot_val = get_crypto_value_eur(db, client_id)
    crypto_positions = CryptoPositionRepository.list_by_client(db, client_id)
    spot_count = sum(1 for p in crypto_positions if Decimal(str(p.balance)) > 0)

    # Lending / borrowing: from pe_position_atoms
    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.client_id == client_id, Portfolio.status == "active")
        .all()
    )
    portfolio_ids = [p.id for p in portfolios]

    lending_val = _ZERO
    borrowing_val = _ZERO
    lending_count = 0
    borrowing_count = 0
    lending_positions = []
    borrowing_positions = []

    if portfolio_ids:
        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id.in_(portfolio_ids),
                PositionAtom.status == "open",
                PositionAtom.quantity > 0,
                PositionAtom.position_type.in_(["lending", "borrowing"]),
            )
            .all()
        )

        for atom in atoms:
            price_usdt = _get_atom_price_usdt(db, atom.instrument_id)
            if price_usdt is None:
                continue

            quantity = Decimal(str(atom.quantity))
            accrued = Decimal(str(atom.accrued_income or 0))
            effective_qty = quantity + accrued
            price_eur = usdt_to_eur(price_usdt, eurusdt_rate)
            val_eur = (effective_qty * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)

            if atom.position_type == "lending":
                lending_val += val_eur
                lending_count += 1
                lending_positions.append(
                    compute_position_market_value(db, atom, eurusdt_rate=eurusdt_rate)
                )
            elif atom.position_type == "borrowing":
                borrowing_val += val_eur
                borrowing_count += 1
                borrowing_positions.append(
                    compute_position_market_value(db, atom, eurusdt_rate=eurusdt_rate)
                )

    net_val = spot_val + lending_val - borrowing_val

    return {
        "spot_value_eur": float(spot_val.quantize(_ROUND)),
        "lending_value_eur": float(lending_val.quantize(_ROUND)),
        "borrowing_value_eur": float(borrowing_val.quantize(_ROUND)),
        "net_value_eur": float(net_val.quantize(_ROUND)),
        "spot_count": spot_count,
        "lending_count": lending_count,
        "borrowing_count": borrowing_count,
        "lending_positions": lending_positions,
        "borrowing_positions": borrowing_positions,
    }


def get_lending_positions(db: Session, client_id: UUID) -> list[dict]:
    """Return all open lending positions for a client, with market values."""
    eurusdt_rate = get_fx_rate(db)

    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.client_id == client_id, Portfolio.status == "active")
        .all()
    )
    portfolio_ids = [p.id for p in portfolios]
    if not portfolio_ids:
        return []

    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id.in_(portfolio_ids),
            PositionAtom.position_type == "lending",
            PositionAtom.status == "open",
            PositionAtom.quantity > 0,
        )
        .all()
    )

    return [compute_position_market_value(db, a, eurusdt_rate=eurusdt_rate) for a in atoms]


def get_borrowing_positions(db: Session, client_id: UUID) -> list[dict]:
    """Return all open borrowing positions for a client, with market values."""
    eurusdt_rate = get_fx_rate(db)

    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.client_id == client_id, Portfolio.status == "active")
        .all()
    )
    portfolio_ids = [p.id for p in portfolios]
    if not portfolio_ids:
        return []

    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id.in_(portfolio_ids),
            PositionAtom.position_type == "borrowing",
            PositionAtom.status == "open",
            PositionAtom.quantity > 0,
        )
        .all()
    )

    return [compute_position_market_value(db, a, eurusdt_rate=eurusdt_rate) for a in atoms]


def _empty_wealth() -> dict:
    return {
        "spot_value_eur": 0.0,
        "lending_value_eur": 0.0,
        "borrowing_value_eur": 0.0,
        "net_value_eur": 0.0,
        "spot_count": 0,
        "lending_count": 0,
        "borrowing_count": 0,
        "lending_positions": [],
        "borrowing_positions": [],
    }
