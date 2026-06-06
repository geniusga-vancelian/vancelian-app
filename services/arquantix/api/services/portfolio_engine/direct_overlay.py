"""Direct Portfolio Overlay — structural separation of direct vs. bundle holdings.

Provides utilities to:
  - auto-provision a ``direct_portfolio`` for a client
  - sync ``pe_position_atoms`` in the direct portfolio on BUY / SELL / SWAP
  - backfill existing direct holdings from crypto_positions minus bundle atoms
  - check Invariant F: direct_atoms + bundle_atoms ≈ crypto_positions
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from services.exchange.models import CryptoPosition
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

logger = logging.getLogger(__name__)

PORTFOLIO_TYPE_DIRECT = "direct_portfolio"
POSITION_TYPE_SPOT = PositionType.SPOT


# ------------------------------------------------------------------
# Auto-provision
# ------------------------------------------------------------------

def ensure_direct_portfolio(db: Session, client_id: UUID) -> Portfolio:
    """Return the client's direct portfolio, creating it if absent."""
    existing = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == PORTFOLIO_TYPE_DIRECT,
            Portfolio.status == "active",
        )
        .first()
    )
    if existing is not None:
        return existing

    portfolio = Portfolio(
        client_id=client_id,
        portfolio_type=PORTFOLIO_TYPE_DIRECT,
        name="Direct Holdings",
        base_currency="USD",
        status="active",
        metadata_={"auto_provisioned": True},
    )
    db.add(portfolio)
    db.flush()
    logger.info("Auto-provisioned direct_portfolio %s for client %s", portfolio.id, client_id)
    return portfolio


# ------------------------------------------------------------------
# Instrument resolution (reuses PE schema)
# ------------------------------------------------------------------

def _resolve_instrument(db: Session, asset_symbol: str) -> Optional[Instrument]:
    """Find the PE instrument for an exchange asset symbol."""
    upper = asset_symbol.upper()
    asset = db.query(Asset).filter(Asset.symbol == upper).first()
    if asset is None:
        return None
    return (
        db.query(Instrument)
        .filter(
            Instrument.asset_id == asset.id,
            Instrument.instrument_type == "spot",
        )
        .first()
    )


def _resolve_or_create_instrument(db: Session, asset_symbol: str) -> Instrument:
    """Find or create the PE instrument for an exchange asset symbol."""
    upper = asset_symbol.upper()
    asset = db.query(Asset).filter(Asset.symbol == upper).first()
    if asset is None:
        asset = Asset(
            symbol=upper,
            name=upper,
            asset_type="stablecoin" if upper in ("USDC", "EURC") else "cryptocurrency",
        )
        db.add(asset)
        db.flush()

    instr = (
        db.query(Instrument)
        .filter(
            Instrument.asset_id == asset.id,
            Instrument.instrument_type == "spot",
        )
        .first()
    )
    if instr is None:
        instr = Instrument(
            asset_id=asset.id,
            code=f"{upper}_SPOT",
            name=f"{upper} Spot",
            instrument_type="spot",
        )
        db.add(instr)
        db.flush()
    return instr


# ------------------------------------------------------------------
# Atom sync (mirror of BundleOrchestrator._sync_pe_position)
# ------------------------------------------------------------------

def sync_direct_atom(
    db: Session,
    portfolio_id: UUID,
    instrument_id: UUID,
    quantity_delta: Decimal,
    cost_basis_delta: Decimal,
) -> PositionAtom:
    """Create or update a direct portfolio spot atom (additive delta)."""
    existing = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
            PositionAtom.status == "open",
        )
        .first()
    )
    if existing is not None:
        existing.quantity = Decimal(str(existing.quantity)) + quantity_delta
        existing.available_quantity = (
            Decimal(str(existing.available_quantity)) + quantity_delta
        )
        cb = Decimal(str(existing.cost_basis or 0))
        existing.cost_basis = cb + cost_basis_delta
        if existing.quantity > 0:
            existing.average_entry_price = existing.cost_basis / existing.quantity
        if existing.quantity <= 0:
            existing.quantity = Decimal("0")
            existing.available_quantity = Decimal("0")
        db.flush()
        return existing

    atom = PositionAtom(
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        position_type=POSITION_TYPE_SPOT,
        status="open",
        quantity=max(quantity_delta, Decimal("0")),
        available_quantity=max(quantity_delta, Decimal("0")),
        cost_basis=max(cost_basis_delta, Decimal("0")),
        average_entry_price=(
            (cost_basis_delta / quantity_delta)
            if quantity_delta > 0
            else Decimal("0")
        ),
        metadata_={"scope": "direct"},
    )
    db.add(atom)
    db.flush()
    return atom


# ------------------------------------------------------------------
# Backfill: compute direct atoms from existing data
# ------------------------------------------------------------------

def _normalize_asset_symbol(symbol: str) -> str:
    mapping = {
        "TBTC": "BTC", "TETH": "ETH", "TSOL": "SOL",
        "TXRP": "XRP", "TADA": "ADA",
    }
    base = symbol.split("_")[0] if "_" in symbol else symbol
    return mapping.get(base, symbol)


def backfill_direct_atoms(db: Session, client_id: UUID) -> dict:
    """Create direct atoms from crypto_positions minus bundle atom quantities.

    Uses WAC from exchange_orders to compute fair cost_basis for each direct atom.
    """
    from services.exchange.repository import ExchangeOrderRepository

    portfolio = ensure_direct_portfolio(db, client_id)

    positions = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == client_id)
        .all()
    )

    bundle_portfolio_ids = [
        row[0] for row in
        db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .all()
    ]

    results = []

    for pos in positions:
        asset = pos.asset.upper()
        total_balance = Decimal(str(pos.balance))
        if total_balance <= 0:
            continue

        instrument = _resolve_instrument(db, asset)
        if instrument is None:
            instrument = _resolve_or_create_instrument(db, asset)

        bundle_qty = Decimal("0")
        if bundle_portfolio_ids:
            row = (
                db.query(sa_func.coalesce(sa_func.sum(PositionAtom.quantity), 0))
                .filter(
                    PositionAtom.portfolio_id.in_(bundle_portfolio_ids),
                    PositionAtom.instrument_id == instrument.id,
                    PositionAtom.position_type == POSITION_TYPE_SPOT,
                    PositionAtom.status == "open",
                )
                .scalar()
            )
            bundle_qty = Decimal(str(row or 0))

        direct_qty = total_balance - bundle_qty
        if direct_qty <= 0:
            results.append({
                "asset": asset,
                "direct_qty": 0,
                "status": "skipped_no_direct",
            })
            continue

        wac_price = _compute_wac_price(db, client_id, asset)
        direct_cost = (direct_qty * wac_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

        if bundle_qty > 0:
            bundle_cost = Decimal("0")
            for pid in bundle_portfolio_ids:
                atom = (
                    db.query(PositionAtom)
                    .filter(
                        PositionAtom.portfolio_id == pid,
                        PositionAtom.instrument_id == instrument.id,
                        PositionAtom.position_type == POSITION_TYPE_SPOT,
                        PositionAtom.status == "open",
                    )
                    .first()
                )
                if atom:
                    bundle_cost += Decimal(str(atom.cost_basis or 0))

            total_wac_cost = (total_balance * wac_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            )
            direct_cost = max(total_wac_cost - bundle_cost, Decimal("0"))

        existing_direct = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio.id,
                PositionAtom.instrument_id == instrument.id,
                PositionAtom.position_type == POSITION_TYPE_SPOT,
                PositionAtom.status == "open",
            )
            .first()
        )
        if existing_direct is not None:
            existing_direct.quantity = direct_qty
            existing_direct.available_quantity = direct_qty
            existing_direct.cost_basis = direct_cost
            if direct_qty > 0:
                existing_direct.average_entry_price = direct_cost / direct_qty
            db.flush()
        else:
            atom = PositionAtom(
                portfolio_id=portfolio.id,
                instrument_id=instrument.id,
                position_type=POSITION_TYPE_SPOT,
                status="open",
                quantity=direct_qty,
                available_quantity=direct_qty,
                cost_basis=direct_cost,
                average_entry_price=(
                    (direct_cost / direct_qty) if direct_qty > 0 else Decimal("0")
                ),
                metadata_={"scope": "direct", "backfilled": True},
            )
            db.add(atom)
            db.flush()

        results.append({
            "asset": asset,
            "direct_qty": float(direct_qty),
            "bundle_qty": float(bundle_qty),
            "direct_cost_basis": float(direct_cost),
            "status": "created",
        })

    return {
        "portfolio_id": str(portfolio.id),
        "backfill_results": results,
    }


def _compute_wac_price(db: Session, client_id: UUID, asset: str) -> Decimal:
    """Compute WAC price from exchange orders (same logic as wallet_statistics)."""
    from services.exchange.models import ExchangeOrder

    buy_orders = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client_id,
            ExchangeOrder.asset == asset,
            ExchangeOrder.side == "buy",
            ExchangeOrder.status == "completed",
        )
        .all()
    )

    total_cost = Decimal("0")
    total_qty = Decimal("0")
    for o in buy_orders:
        qty = Decimal(str(o.amount_crypto or 0))
        fiat = Decimal(str(o.amount_fiat or 0))
        total_qty += qty
        total_cost += fiat

    if total_qty > 0:
        return total_cost / total_qty
    return Decimal("0")


# ------------------------------------------------------------------
# Custody → PE trading_available (Privy-only gaps, ex. EURC)
# ------------------------------------------------------------------

_ALIGN_TOLERANCE = Decimal("0.000001")


def _align_tolerance(asset: str) -> Decimal:
    if asset.upper() in ("USDC", "USDT", "EURC", "DAI"):
        return Decimal("0.01")
    return _ALIGN_TOLERANCE


def align_pe_trading_available_from_ledger_liquid(
    db: Session,
    person_id: UUID,
) -> list[dict[str, str]]:
    """Aligne ``trading_available`` PE (direct_portfolio) sur le ledger Privy liquide.

    Formule : ``ledger_balance - vault_position - locked_collateral`` (doctrine custody).
    Ne touche pas ``person_wallet_balances`` ; ne réduit jamais un atom direct existant.
    Ignore les actifs avec collateral Lombard verrouillé (scopes gérés ailleurs).
    """
    from services.portfolio_engine.bundle_execution.bundle_cost_basis import reference_cost_basis_eur
    from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
    from services.portfolio_engine.internal_scope_movements.utils import resolve_client_id
    from services.privy_wallet.repository import PersonWalletBalanceRepository

    client_id = resolve_client_id(db, person_id)
    if client_id is None:
        return []

    pe = read_current_pe_scope_snapshot(db, person_id)
    ledger: dict[str, Decimal] = {}
    for row in PersonWalletBalanceRepository.list_for_person(db, person_id):
        asset = str(row.asset).upper()
        ledger[asset] = ledger.get(asset, Decimal("0")) + Decimal(str(row.balance or 0))

    if not ledger:
        return []

    direct_pf = ensure_direct_portfolio(db, client_id)
    aligned: list[dict[str, str]] = []

    for asset, ledger_bal in sorted(ledger.items()):
        if ledger_bal <= 0:
            continue
        vault_alloc = pe.vault_position.get(asset, Decimal("0"))
        locked_collateral = pe.trading_locked_collateral.get(asset, Decimal("0"))
        if locked_collateral > _align_tolerance(asset):
            continue

        current_avail = pe.trading_available.get(asset, Decimal("0"))
        expected_avail = max(Decimal("0"), ledger_bal - vault_alloc - locked_collateral)
        delta = expected_avail - current_avail
        tol = _align_tolerance(asset)
        if delta <= tol:
            continue

        instrument = _resolve_or_create_instrument(db, asset)
        cost_basis = reference_cost_basis_eur(db, asset, delta)
        sync_direct_atom(
            db,
            direct_pf.id,
            instrument.id,
            delta,
            cost_basis,
        )
        aligned.append(
            {
                "asset": asset,
                "delta": str(delta.normalize()),
                "expected_trading_available": str(expected_avail.normalize()),
                "previous_trading_available": str(current_avail.normalize()),
            }
        )
        logger.info(
            "direct_overlay.align_trading_available client=%s asset=%s delta=%s expected=%s",
            client_id,
            asset,
            delta,
            expected_avail,
        )
    return aligned


# ------------------------------------------------------------------
# Invariant F: direct + bundle = crypto_positions
# ------------------------------------------------------------------

def check_invariant_f(db: Session, client_id: UUID) -> dict:
    """Verify Invariant F: Σ direct_atoms + Σ bundle_atoms ≈ crypto_positions.balance per asset.

    Tolerance: 0.000001 (rounding artefacts).
    """
    TOLERANCE = Decimal("0.000001")

    portfolio_ids = [
        row[0] for row in
        db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type.in_([PORTFOLIO_TYPE_DIRECT, "bundle_portfolio"]),
        )
        .all()
    ]

    pe_sums: dict[str, Decimal] = {}
    if portfolio_ids:
        rows = (
            db.query(
                Asset.symbol,
                sa_func.coalesce(sa_func.sum(PositionAtom.quantity), 0).label("total"),
            )
            .join(Instrument, Instrument.id == PositionAtom.instrument_id)
            .join(Asset, Asset.id == Instrument.asset_id)
            .filter(
                PositionAtom.portfolio_id.in_(portfolio_ids),
                PositionAtom.position_type == POSITION_TYPE_SPOT,
                PositionAtom.status == "open",
            )
            .group_by(Asset.symbol)
            .all()
        )
        for symbol, total in rows:
            normalized = _normalize_asset_symbol(symbol.upper())
            pe_sums[normalized] = pe_sums.get(normalized, Decimal("0")) + Decimal(str(total))

    crypto_positions = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == client_id)
        .all()
    )
    balance_map = {p.asset.upper(): Decimal(str(p.balance)) for p in crypto_positions}

    all_assets = set(pe_sums.keys()) | set(balance_map.keys())
    violations = []
    all_ok = True

    for asset in sorted(all_assets):
        pe_total = pe_sums.get(asset, Decimal("0"))
        exchange_balance = balance_map.get(asset, Decimal("0"))
        delta = abs(pe_total - exchange_balance)
        ok = delta <= TOLERANCE

        if not ok:
            all_ok = False
            violations.append({
                "asset": asset,
                "pe_total": float(pe_total),
                "exchange_balance": float(exchange_balance),
                "delta": float(pe_total - exchange_balance),
            })

    return {
        "invariant_f_ok": all_ok,
        "checked_assets": len(all_assets),
        "violations": violations,
    }
