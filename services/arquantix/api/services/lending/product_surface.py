"""Earn / Borrow Product Surface — Phase 2A.9 (improved).

Aggregation layer that exposes the pool lending engine as a clean product:
  - Earn: lender-facing view with earning/idle split + accrued interest
  - Borrow: borrower-facing view (borrow positions + accrued interest + total due)
  - Pools: market-facing overview (liquidity, rates, utilization, APY vs APR)

This module is READ-ONLY — it does not modify any data.
All mutations go through the existing pool_service, repayment_engine, interest_engine.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.portfolios.models import Portfolio

from .envelope_models import InvestmentEnvelope, InvestmentEnvelopeEntry
from .pool_models import LendingPool, PoolSupplyCommitment, PoolBorrowPosition, PoolAllocation
from .offer_models import LendingPoolProduct
from .valuation import _get_atom_price_usdt, _get_atom_asset_symbol, get_fx_rate

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_ROUND = Decimal("0.01")
_BPS_TO_PCT = Decimal("100")

_APY_EXPLANATION = "APY estimé basé sur l'utilisation actuelle de la pool. Le rendement réel dépend du taux d'emprunt futur."


def _bps_to_pct(bps: Decimal) -> float:
    """Convert basis points to percentage (500 bps → 5.00)."""
    return float((bps / _BPS_TO_PCT).quantize(_ROUND, rounding=ROUND_HALF_UP))


def _get_price_eur(db: Session, asset: str, eurusdt_rate: Decimal):
    """Return (price_usdt, price_eur) for an asset, using instrument lookup."""
    from services.portfolio_engine.direct_overlay import _resolve_or_create_instrument
    from services.market_data.fx import usdt_to_eur

    instrument = _resolve_or_create_instrument(db, asset)
    if not instrument:
        return None, _ZERO
    price_usdt = _get_atom_price_usdt(db, instrument.id)
    if price_usdt is None:
        return None, _ZERO
    return price_usdt, usdt_to_eur(price_usdt, eurusdt_rate)


# ── POOLS OVERVIEW ────────────────────────────────────────────────

def get_pools_overview(db: Session) -> list[dict]:
    """All active pools with rates, utilization, and APY clarification."""
    pools = db.query(LendingPool).filter(LendingPool.status == "active").all()
    result = []
    for pool in pools:
        total_committed = Decimal(str(pool.total_committed))
        total_borrowed = Decimal(str(pool.total_borrowed))
        available = total_committed - total_borrowed

        utilization = (
            float((total_borrowed / total_committed * Decimal("100")).quantize(_ROUND))
            if total_committed > 0 else 0.0
        )

        supply_apr = _bps_to_pct(Decimal(str(pool.supply_rate_bps)))
        borrow_apr = _bps_to_pct(Decimal(str(pool.borrow_rate_bps)))

        # effective_apy = supply_apr × utilization (only earning portion generates yield)
        effective_apy = (
            float(
                (Decimal(str(pool.supply_rate_bps)) / _BPS_TO_PCT
                 * total_borrowed / total_committed).quantize(_ROUND)
            )
            if total_committed > 0 else 0.0
        )

        result.append({
            "asset": pool.asset,
            "pool_id": str(pool.id),
            "total_supplied": float(total_committed.quantize(_ROUND)),
            "total_borrowed": float(total_borrowed.quantize(_ROUND)),
            "available_liquidity": float(available.quantize(_ROUND)),
            "utilization": utilization,
            "supply_apr": supply_apr,
            "borrow_apr": borrow_apr,
            "effective_apy": effective_apy,
            "is_apy_estimated": True,
            "apy_explanation": _APY_EXPLANATION,
        })

    return sorted(result, key=lambda p: p["total_supplied"], reverse=True)


# ── EARN POSITIONS (lender view) — earning / idle split ──────────

def get_earn_positions(db: Session, client_id: UUID) -> dict:
    """Lender-facing aggregation with earning/idle split per asset.

    earning = funds actively lent (lending atoms with accrued interest)
    idle     = committed but not yet consumed by borrows
    """
    from services.market_data.fx import usdt_to_eur

    eurusdt_rate = get_fx_rate(db)

    # ── 1. Lending atoms → earning amounts per asset ──────────────
    portfolios = db.query(Portfolio).filter(
        Portfolio.client_id == client_id, Portfolio.status == "active",
    ).all()
    portfolio_ids = [p.id for p in portfolios]

    # Per-asset earning data: { asset: { quantity, accrued, value_eur, accrued_eur } }
    earning_by_asset: dict[str, dict] = {}

    if portfolio_ids:
        atoms = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id.in_(portfolio_ids),
            PositionAtom.position_type == "lending",
            PositionAtom.status == "open",
            PositionAtom.quantity > 0,
        ).all()

        for atom in atoms:
            quantity = Decimal(str(atom.quantity))
            accrued = Decimal(str(atom.accrued_income or 0))
            total_qty = quantity + accrued

            asset_symbol = _get_atom_asset_symbol(db, atom.instrument_id)
            price_usdt = _get_atom_price_usdt(db, atom.instrument_id)

            if price_usdt and asset_symbol:
                price_eur = usdt_to_eur(price_usdt, eurusdt_rate)
                value_eur = (total_qty * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
                accrued_eur = (accrued * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
            else:
                value_eur = _ZERO
                accrued_eur = _ZERO

            if asset_symbol:
                prev = earning_by_asset.get(asset_symbol, {
                    "quantity": _ZERO, "accrued": _ZERO,
                    "value_eur": _ZERO, "accrued_eur": _ZERO,
                })
                earning_by_asset[asset_symbol] = {
                    "quantity": prev["quantity"] + quantity,
                    "accrued": prev["accrued"] + accrued,
                    "value_eur": prev["value_eur"] + value_eur,
                    "accrued_eur": prev["accrued_eur"] + accrued_eur,
                }

    # ── 2. All commitments for this client (active/partially_used) ─
    all_commitments = db.query(PoolSupplyCommitment).filter(
        PoolSupplyCommitment.client_id == client_id,
        PoolSupplyCommitment.status.in_(["active", "partially_used"]),
    ).all()

    pending_list = []
    for c in all_commitments:
        if Decimal(str(c.available_amount)) > 0:
            pool = db.query(LendingPool).filter(LendingPool.id == c.pool_id).first()
            pending_list.append({
                "commitment_id": str(c.id),
                "asset": c.asset,
                "committed": float(c.amount),
                "available": float(c.available_amount),
                "status": c.status,
                "supply_apr": _bps_to_pct(Decimal(str(pool.supply_rate_bps))) if pool else 0.0,
            })

    # ── 2b. Envelope entries for this client (Phase 2A.16) ─────────
    envelope_data_by_commitment: dict[str, dict] = {}
    try:
        entries = (
            db.query(InvestmentEnvelopeEntry)
            .join(InvestmentEnvelope, InvestmentEnvelopeEntry.envelope_id == InvestmentEnvelope.id)
            .filter(
                InvestmentEnvelope.client_id == client_id,
                InvestmentEnvelope.status == "active",
            )
            .all()
        )
        for e in entries:
            if e.commitment_id:
                envelope_data_by_commitment[str(e.commitment_id)] = {
                    "entry_asset": e.entry_asset,
                    "entry_amount": float(e.entry_amount),
                    "converted_amount": float(e.converted_amount),
                    "conversion_type": e.conversion_type,
                    "conversion_fee": float(e.conversion_fee),
                    "net_allocated": float(e.net_allocated),
                }
    except Exception:
        pass

    # ── 3. Aggregate per POOL (not per asset) ─────────────────────
    #    Each exclusive offer has its own pool, so aggregating per pool
    #    produces one position per offer — even if multiple offers share
    #    the same asset (e.g. two USDC offers).

    # Group commitments by pool_id
    commitments_by_pool: dict[str, list[PoolSupplyCommitment]] = defaultdict(list)
    for c in all_commitments:
        commitments_by_pool[str(c.pool_id)].append(c)

    positions = []
    total_earn_eur = _ZERO
    total_accrued_eur = _ZERO
    total_earning_eur = _ZERO
    total_idle_eur = _ZERO

    for pool_id_str, pool_commitments in commitments_by_pool.items():
        pool = db.query(LendingPool).filter(
            LendingPool.id == pool_commitments[0].pool_id,
        ).first()
        if not pool:
            continue

        asset = pool.asset
        _, price_eur = _get_price_eur(db, asset, eurusdt_rate)

        # Sum committed and idle for this pool
        pool_total_committed = sum(Decimal(str(c.amount)) for c in pool_commitments)
        pool_idle = sum(Decimal(str(c.available_amount)) for c in pool_commitments)

        # Earning = committed - idle (funds actively lent)
        pool_earning = pool_total_committed - pool_idle

        # Accrued interest from lending atoms linked to this pool's allocations
        accrued = _ZERO
        pool_allocs = db.query(PoolAllocation).filter(
            PoolAllocation.supply_commitment_id.in_([c.id for c in pool_commitments]),
        ).all()
        for alloc in pool_allocs:
            if alloc.lending_position_atom_id:
                atom = db.query(PositionAtom).filter(
                    PositionAtom.id == alloc.lending_position_atom_id,
                    PositionAtom.status == "open",
                ).first()
                if atom and atom.accrued_income:
                    accrued += Decimal(str(atom.accrued_income))

        total_supplied = pool_total_committed
        total_value = total_supplied + accrued

        earning_value_eur = (pool_earning * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
        idle_value_eur = (pool_idle * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
        accrued_eur = (accrued * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
        pos_value_eur = earning_value_eur + idle_value_eur

        # Pool rates
        apy = 0.0
        pool_util = 0.0
        tc = Decimal(str(pool.total_committed))
        tb = Decimal(str(pool.total_borrowed))
        if tc > 0:
            apy = float(
                (Decimal(str(pool.supply_rate_bps)) / _BPS_TO_PCT
                 * tb / tc).quantize(_ROUND)
            )
            pool_util = float((tb / tc * Decimal("100")).quantize(_ROUND))

        total_earn_eur += pos_value_eur
        total_accrued_eur += accrued_eur
        total_earning_eur += earning_value_eur
        total_idle_eur += idle_value_eur

        # Resolve product + project
        product = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.lending_pool_id == pool.id,
        ).first()

        # Resolve envelope data for this pool's commitments
        envelope_info = None
        for c in pool_commitments:
            cid = str(c.id)
            if cid in envelope_data_by_commitment:
                envelope_info = envelope_data_by_commitment[cid]
                break

        positions.append({
            "asset": asset,
            "pool_id": pool_id_str,
            "lending_pool_product_id": str(product.id) if product else None,
            "project_id": product.project_id if product else None,
            "total_supplied": float(total_supplied),
            "earning_amount": float(pool_earning),
            "idle_amount": float(pool_idle),
            "accrued_interest": float(accrued),
            "total_value": float(total_value),
            "value_eur": float(pos_value_eur),
            "accrued_interest_eur": float(accrued_eur),
            "earning_value_eur": float(earning_value_eur),
            "idle_value_eur": float(idle_value_eur),
            "apy": apy,
            "is_apy_estimated": True,
            "pool_utilization": pool_util,
            "envelope": envelope_info,
            "supplied": float(pool_earning),
        })

    return {
        "total_earn_value_eur": float(total_earn_eur),
        "total_accrued_interest_eur": float(total_accrued_eur),
        "total_supplied_assets": len(positions),
        "earning": {
            "amount_eur": float(total_earning_eur),
            "accrued_interest_eur": float(total_accrued_eur),
        },
        "idle": {
            "amount_eur": float(total_idle_eur),
            "accrued_interest_eur": 0.0,
        },
        "positions_count": len(positions),
        "positions": positions,
        "pending_commitments_count": len(pending_list),
        "pending_commitments": pending_list,
    }


# ── BORROW POSITIONS (borrower view) ─────────────────────────────

def get_borrow_positions(db: Session, client_id: UUID) -> dict:
    """Borrower-facing aggregation: active borrows + accrued interest + total due."""
    from services.market_data.fx import usdt_to_eur

    eurusdt_rate = get_fx_rate(db)

    borrows = db.query(PoolBorrowPosition).filter(
        PoolBorrowPosition.client_id == client_id,
        PoolBorrowPosition.status == "active",
    ).order_by(PoolBorrowPosition.created_at.desc()).all()

    portfolios = db.query(Portfolio).filter(
        Portfolio.client_id == client_id, Portfolio.status == "active",
    ).all()
    portfolio_ids = [p.id for p in portfolios]

    atom_cache: dict[str, PositionAtom] = {}
    if portfolio_ids:
        atoms = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id.in_(portfolio_ids),
            PositionAtom.position_type == "borrowing",
            PositionAtom.status == "open",
        ).all()
        for a in atoms:
            sym = _get_atom_asset_symbol(db, a.instrument_id)
            if sym:
                atom_cache[sym] = a

    positions = []
    total_borrowed_eur = _ZERO
    total_interest_eur = _ZERO

    for bp in borrows:
        principal = Decimal(str(bp.borrowed_amount))
        asset = bp.asset

        atom = atom_cache.get(asset)
        if atom:
            atom_qty = Decimal(str(atom.quantity))
            atom_accrued = Decimal(str(atom.accrued_income or 0))
            if atom_qty > 0:
                share = principal / atom_qty
                accrued = (atom_accrued * share).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)
            else:
                accrued = _ZERO
        else:
            accrued = _ZERO

        total_due = principal + accrued

        _, price_eur = _get_price_eur(db, asset, eurusdt_rate)

        due_eur = (total_due * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
        accrued_eur = (accrued * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)
        principal_eur = (principal * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP)

        pool = db.query(LendingPool).filter(LendingPool.id == bp.pool_id).first()
        apr = _bps_to_pct(Decimal(str(pool.borrow_rate_bps))) if pool else 0.0

        total_borrowed_eur += principal_eur
        total_interest_eur += accrued_eur

        positions.append({
            "borrow_position_id": str(bp.id),
            "asset": asset,
            "borrowed": float(principal),
            "accrued_interest": float(accrued),
            "total_due": float(total_due),
            "value_eur": float(due_eur),
            "accrued_interest_eur": float(accrued_eur),
            "apr": apr,
            "created_at": bp.created_at.isoformat() if bp.created_at else None,
        })

    return {
        "total_borrowed_eur": float(total_borrowed_eur),
        "total_interest_due_eur": float(total_interest_eur),
        "total_due_eur": float((total_borrowed_eur + total_interest_eur).quantize(_ROUND)),
        "positions_count": len(positions),
        "positions": positions,
    }


# ── EARN/BORROW DASHBOARD (combined) ─────────────────────────────

def get_earn_borrow_dashboard(db: Session, client_id: UUID) -> dict:
    """Combined dashboard for Earn + Borrow — single call for the main screen."""
    earn = get_earn_positions(db, client_id)
    borrow = get_borrow_positions(db, client_id)

    return {
        "earn": {
            "total_value_eur": earn["total_earn_value_eur"],
            "accrued_interest_eur": earn["total_accrued_interest_eur"],
            "positions_count": earn["positions_count"],
            "pending_commitments_count": earn["pending_commitments_count"],
        },
        "earn_breakdown": {
            "earning_value_eur": earn["earning"]["amount_eur"],
            "idle_value_eur": earn["idle"]["amount_eur"],
            "accrued_interest_eur": earn["earning"]["accrued_interest_eur"],
        },
        "borrow": {
            "total_borrowed_eur": borrow["total_borrowed_eur"],
            "total_interest_due_eur": borrow["total_interest_due_eur"],
            "total_due_eur": borrow["total_due_eur"],
            "positions_count": borrow["positions_count"],
        },
        "net_position_eur": float(
            Decimal(str(earn["total_earn_value_eur"]))
            - Decimal(str(borrow["total_due_eur"]))
        ),
    }
