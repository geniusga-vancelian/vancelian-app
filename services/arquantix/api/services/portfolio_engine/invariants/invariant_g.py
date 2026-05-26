"""Invariant G — PE sub-ledger vs Privy on-chain balances (Phase 1 skeleton).

Definition (target, per asset and optionally per chain)::

    balance_privy(asset, chain)
    ≈ atom_direct(asset)
      + Σ atom_bundles(asset)
      + atom_vaults(asset)      # not included until vaults are modeled in PE
      + reserved_pending(asset) # Phase 4

Phase 1: dry_run only — never blocks operations.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from database import Person
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

logger = logging.getLogger(__name__)

TOLERANCE = Decimal("0.000001")
_VAULTS_INCLUDED = False


def _normalize_asset(symbol: str) -> str:
    mapping = {
        "TBTC": "BTC", "TETH": "ETH", "TSOL": "SOL",
        "TXRP": "XRP", "TADA": "ADA",
    }
    base = symbol.split("_")[0] if "_" in symbol else symbol
    return mapping.get(base.upper(), base.upper())


def _sum_pe_atoms_by_asset(
    db: Session,
    client_id: UUID,
    *,
    portfolio_types: tuple[str, ...],
) -> dict[str, Decimal]:
    rows = (
        db.query(
            Asset.symbol,
            sa_func.coalesce(sa_func.sum(PositionAtom.quantity), 0).label("total"),
        )
        .join(Instrument, Instrument.id == PositionAtom.instrument_id)
        .join(Asset, Asset.id == Instrument.asset_id)
        .join(Portfolio, Portfolio.id == PositionAtom.portfolio_id)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type.in_(portfolio_types),
            PositionAtom.position_type == PositionType.SPOT,
            PositionAtom.status == "open",
        )
        .group_by(Asset.symbol)
        .all()
    )
    out: dict[str, Decimal] = {}
    for symbol, total in rows:
        key = _normalize_asset(symbol)
        out[key] = out.get(key, Decimal("0")) + Decimal(str(total))
    return out


def _privy_balances_by_asset(db: Session, person_id: UUID) -> dict[str, Decimal] | None:
    try:
        from services.privy_wallet.chain_balance import (
            aggregate_confirmed_deposit_balances,
            reconcile_chain_buckets_with_ledger,
        )
        from services.privy_wallet.repository import PersonCryptoWalletRepository
    except ImportError:
        return None

    wallets = PersonCryptoWalletRepository().list_active_for_person(db, person_id)
    if not wallets:
        return {}

    buckets = reconcile_chain_buckets_with_ledger(
        db,
        person_id=person_id,
        wallets=wallets,
        buckets=aggregate_confirmed_deposit_balances(
            db, person_id=person_id, wallets=wallets,
        ),
    )
    out: dict[str, Decimal] = {}
    for bucket in buckets:
        asset = bucket.asset.upper()
        out[asset] = out.get(asset, Decimal("0")) + Decimal(str(bucket.balance))
    return out


def check_invariant_g(
    db: Session,
    client_id: UUID,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Compare Privy on-chain balances to PE atoms (direct + bundles).

    Returns ``status``: ``ok`` | ``violation`` | ``unavailable`` | ``skipped``.
    """
    _ = dry_run  # Phase 1: never blocks regardless of flag

    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        return {
            "invariant_g_ok": False,
            "status": "skipped",
            "reason": "client_not_found",
            "dry_run": True,
        }

    direct = _sum_pe_atoms_by_asset(db, client_id, portfolio_types=("direct_portfolio",))
    bundles = _sum_pe_atoms_by_asset(db, client_id, portfolio_types=("bundle_portfolio",))

    if client.person_id is None:
        return {
            "invariant_g_ok": True,
            "status": "unavailable",
            "reason": "no_person_id_for_privy",
            "dry_run": True,
            "direct_atoms": {k: float(v) for k, v in direct.items()},
            "bundle_atoms": {k: float(v) for k, v in bundles.items()},
            "vault_atoms_included": _VAULTS_INCLUDED,
            "reserved_pending_included": False,
            "violations": [],
        }

    person = db.query(Person).filter(Person.id == client.person_id).first()
    if person is None:
        return {
            "invariant_g_ok": True,
            "status": "unavailable",
            "reason": "person_not_found",
            "dry_run": True,
            "violations": [],
        }

    privy = _privy_balances_by_asset(db, client.person_id)
    if privy is None:
        return {
            "invariant_g_ok": True,
            "status": "unavailable",
            "reason": "privy_module_unavailable",
            "dry_run": True,
            "violations": [],
        }

    all_assets = set(direct) | set(bundles) | set(privy)
    violations: list[dict[str, Any]] = []

    for asset in sorted(all_assets):
        d = direct.get(asset, Decimal("0"))
        b = bundles.get(asset, Decimal("0"))
        p = privy.get(asset, Decimal("0"))
        pe_total = d + b
        delta = abs(pe_total - p)
        if delta > TOLERANCE:
            violations.append({
                "asset": asset,
                "privy_balance": float(p),
                "direct_atoms": float(d),
                "bundle_atoms": float(b),
                "pe_total_atoms": float(pe_total),
                "delta": float(pe_total - p),
            })

    ok = len(violations) == 0 and bool(all_assets or privy == {})
    return {
        "invariant_g_ok": ok,
        "status": "ok" if ok else "violation",
        "dry_run": True,
        "checked_assets": len(all_assets),
        "direct_atoms": {k: float(v) for k, v in direct.items()},
        "bundle_atoms": {k: float(v) for k, v in bundles.items()},
        "privy_balances": {k: float(v) for k, v in privy.items()},
        "vault_atoms_included": _VAULTS_INCLUDED,
        "reserved_pending_included": False,
        "violations": violations,
        "notes": [
            "Vault positions are not yet summed in pe_position_atoms.",
            "reserved_pending is Phase 4; not applied in Phase 1.",
            "Invariant G is dry_run only and does not block operations.",
        ],
    }
